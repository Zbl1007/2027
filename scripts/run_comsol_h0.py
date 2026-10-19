#!/usr/bin/env python3
"""Build/solve only H0 through the installed COMSOL Java API; never synthesize fields.

Every invocation creates a new evidence directory, preserving failed attempts.
Requires COMSOL's own Windows compile/batch executables and a usable license.
"""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, read_field, analytic_h0, write_json


def read_log(path):
    raw=path.read_bytes()
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('gb18030')  # Chinese Windows launcher stdout; raw log is retained.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comsol-root', type=Path, required=True)
    args = parser.parse_args()
    now = lambda: datetime.now(timezone(timedelta(hours=8))).isoformat()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S%f')
    out = ROOT / 'outputs/comsol_h0' / stamp
    out.mkdir(parents=True, exist_ok=False)
    print(f'Evidence directory: {out}', flush=True)
    events = []

    def run(command, log, cwd=ROOT):
        event = {'command': [str(x) for x in command], 'cwd': str(cwd), 'started_at': now(), 'log': str(log.relative_to(out))}
        events.append(event)
        write_json(out/'operations.json', events)
        with log.open('wb') as stream:
            proc = subprocess.run(event['command'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        event.update(returncode=proc.returncode, finished_at=now(), sha256=digest(log))
        write_json(out/'operations.json', events)
        print(f'{log.name}: return code {proc.returncode}', flush=True)
        if proc.returncode:
            raise RuntimeError(f'Command failed; inspect {log}')

    try:
        folder = PACKAGE/'h0_z16'
        if not folder.is_dir():
            raise FileNotFoundError('Extract the supplied deliverable without replacing existing files before running')
        contract = json.loads((folder/'contract.json').read_text())
        manifest = json.loads((PACKAGE/'manifest.json').read_text())
        entry = next(e for e in manifest['cases'] if e['case_id']=='h0_z16')
        if digest(folder/'contract.json') != entry['contract_sha256'] or digest(DEFINITION) != contract['definition_sha256']:
            raise ValueError('Contract/definition hash mismatch')
        data = load_definition()
        local = json.loads((folder/'3dice_result.json').read_text())
        for name, sha in local['artifacts_sha256'].items():
            if digest(folder/name) != sha:
                raise ValueError('Changed 3D-ICE evidence: '+name)
        metadata_path = out/'metadata.json'
        shutil.copy2(folder/'return_metadata_template.json', metadata_path)
        template = ROOT/'scripts/comsol/H0Thermal.java'
        comp = args.comsol_root/'bin/win64/comsolcompile.exe'
        batch = args.comsol_root/'bin/win64/comsolbatch.exe'
        env = {'started_at': now(), 'platform': platform.platform(), 'python': sys.executable,
               'comsol_root': str(args.comsol_root), 'scope': 'H0 only; synthetic_fixture; no research parameter adoption',
               'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'git_status_at_start': subprocess.check_output(['git','status','--short','--branch'],cwd=ROOT,text=True),
               'input_sha256': {str(p.relative_to(ROOT)):digest(p) for p in [DEFINITION,folder/'contract.json',folder/'comsol_parameters.txt',folder/'sample_points_m.txt',template,Path(__file__)]},
               'executables_sha256': {str(p):digest(p) for p in [comp,batch]}}
        write_json(out/'environment.json',env)
        run([batch,'-version'],out/'version.log')
        metrics = {}
        parameters = '\n    '.join('m.param().set('+json.dumps(name)+','+json.dumps(expr)+');'
                                  for name,expr in (line.split(None,1) for line in (folder/'comsol_parameters.txt').read_text().splitlines()))
        points=[line.split() for line in (folder/'sample_points_m.txt').read_text().splitlines()]
        if len(points)!=16 or any(len(p)!=3 for p in points):
            raise ValueError('H0 requires exactly sixteen original 3D coordinates')
        coordinates='new double[][]{'+','.join('{'+','.join(p[k] for p in points)+'}' for k in range(3))+'}'
        for level,nxy,nz in [('base',2,8),('refined',4,16)]:
            build = out/level
            build.mkdir()
            source = template.read_text(encoding='utf-8')
            for key, value in {'__INPUT_DIR__':folder.as_posix(),'__RUN_DIR__':out.as_posix(),
                               '__LEVEL__':level,'__NXY__':str(nxy),'__NZ__':str(nz),
                               '__PARAMETERS__':parameters,'__COORDINATES__':coordinates}.items():
                source=source.replace(key,value)
            java=build/'H0Thermal.java'
            java.write_text(source,encoding='utf-8')
            run([comp,java],out/f'compile_{level}.log',cwd=build)
            if not java.with_suffix('.class').is_file():
                raise RuntimeError('Compilation did not produce a class file')
            run([batch,'-np','2','-inputfile',java.with_suffix('.class'),'-outputfile',build/'batch_output.mph',
                 '-batchlog',out/f'solver_{level}.log'],out/f'launch_{level}.log',cwd=build)
            raw=read_log(out/f'solver_{level}.log')+'\n'+read_log(out/f'launch_{level}.log')
            results=re.findall(r'H0_RESULT (\{[^\r\n]+\})',raw)
            samples=re.findall(r'H0_TEMPERATURE ([^\r\n]+)',raw)
            if len(results)!=1 or len(samples)!=16:
                raise RuntimeError(f'COMSOL did not produce complete solved evidence; inspect solver_{level}.log and launch_{level}.log (process exit code alone is insufficient)')
            metrics[level]=json.loads(results[0])
            dof=re.search(r'求解的自由度数[：:]\s*(\d+)（加上\s*(\d+)\s*个内部自由度',raw)
            if dof is None:
                dof=re.search(r'Number of degrees of freedom solved for:\s*(\d+)\s*\(plus\s*(\d+)\s*internal',raw)
            if dof is None:
                raise RuntimeError('Cannot identify solved/internal DOF in actual COMSOL log')
            metrics[level]['mesh_dof']=int(dof[1])
            metrics[level]['internal_dof']=int(dof[2])
            if sum(int(dof[i]) for i in [1,2])!=metrics[level]['solution_vector_length']:
                raise RuntimeError('Solver log and saved solution vector dimensions disagree')
            readback=re.search(r'H0_READBACK max_abs_temperature_difference_k=([^\r\n]+)',raw)
            if readback is None:
                raise RuntimeError('Saved MPH readback verification missing')
            metrics[level]['mph_readback_max_abs_difference_k']=float(readback[1])
            write_json(out/f'metrics_{level}.json',metrics[level])
            (out/f'temperature_{level}.csv').write_text('x_m,y_m,z_m,temperature_k\n'+'\n'.join(samples)+'\n',encoding='utf-8')
            if metrics[level]['status']!='solved':
                raise RuntimeError('COMSOL did not finish')
        with (out/'solver.log').open('w',encoding='utf-8',newline='\n') as combined:
            for level in ['base','refined']:
                combined.write(f'===== COMSOL {level} mesh =====\n')
                combined.write(read_log(out/f'solver_{level}.log'))
                combined.write('\n')
                combined.write(read_log(out/f'launch_{level}.log'))
        m=json.loads(metadata_path.read_text())
        m.update(status='solved',solver_version=read_log(out/'version.log').strip(),solved_at=now(),
                 operator='Codex via COMSOL Java API / comsolbatch on user-authorized local machine',
                 notes='H0 only. Constant silicon, uniform volume source, top convection, other faces insulated. '
                 'Mapped bottom plus swept hex mesh: base 2x2x8, refined 4x4x16. Quadratic temperature; stationary linear PARDISO. '
                 'COMSOL Interp evaluates the solved finite-element field at the original 16 sample coordinates, with extrapolation disabled. '
                 'Integrals are COMSOL IntVolume/IntSurface evaluations. Separate solved MPH files retain both meshes. '
                 'Both saved MPH files are reopened and their solved samples re-evaluated. '
                 'DOF fields report solved DOF; internal DOF and full vector sizes are recorded separately. '
                 'solver.log is losslessly decoded to UTF-8; original per-process logs retain their original encoding. '
                 'Analytic reference is used only after solving, in an independent comparison report.',
                 base_mesh_dof=metrics['base']['mesh_dof'],refined_mesh_dof=metrics['refined']['mesh_dof'],
                 integrated_source_w=metrics['refined']['integrated_source_w'],
                 integrated_top_outward_heat_w=metrics['refined']['integrated_top_outward_heat_w'],mesh_metrics=metrics)
        m['evidence']={role:{'file':name,'sha256':digest(out/name)} for role,name in
                       [('model','h0_refined.mph'),('solver_log','solver.log'),('base_model','h0_base.mph')]}
        m['artifacts_sha256']={p.name:digest(p) for p in out.iterdir() if p.is_file() and p.name not in ['metadata.json','operations.json']}
        write_json(metadata_path,m)
        run([sys.executable,'-X','utf8',ROOT/'scripts/import_comsol.py','h0_z16',out],out/'import.log')
        analytic={}
        for level in ['base','refined']:
            field=read_field(out/f'temperature_{level}.csv')
            errors=[r['temperature_k']-analytic_h0(data,r['z_m']) for r in field]
            analytic[level]={'max_abs_error_k':max(map(abs,errors)),
                             'rms_error_k':(sum(e*e for e in errors)/len(errors))**0.5,
                             'sample_count':len(field),'errors_k':errors}
        write_json(out/'analytic_check.json',{'reference_kind':'closed_form_comparison_only_not_solver_output','meshes':analytic})
        write_json(out/'run_status.json',{'status':'solved_and_import_pass','finished_at':now()})
        print(json.dumps({'result_dir':str(out),'metrics':metrics,'analytic':analytic},indent=2),flush=True)
    except Exception as exc:
        write_json(out/'run_status.json',{'status':'failed','finished_at':now(),'reason':str(exc)})
        raise


if __name__=='__main__':
    main()
