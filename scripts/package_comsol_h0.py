#!/usr/bin/env python3
"""Package verified H0 evidence without replacing any earlier deliverable."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile
from coupon_common import ROOT, PACKAGE, digest, write_json
from import_comsol import evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result_dir',type=Path)
    parser.add_argument('zip_path',type=Path)
    args=parser.parse_args()
    result=args.result_dir.resolve()
    target=args.zip_path.resolve()
    if not result.is_relative_to(ROOT) or not target.is_relative_to(ROOT):
        raise ValueError('All outputs must stay in this project')
    if target.exists():
        raise FileExistsError(target)
    report,_=evaluate('h0_z16',result)
    if report['status']!='thermal_comparison_pass':
        raise ValueError('H0 comparison has not passed')
    names=set()
    for p in result.rglob('*'):
        if p.is_file() and p.suffix not in {'.mphstatus','.mphbin'} and not p.name.startswith('batch_output'):
            names.add(p)
    for directory in [PACKAGE/'h0_z16',ROOT/'verification/comsol_imports/h0_z16']:
        names.update(p for p in directory.rglob('*') if p.is_file())
    for name in ['.gitattributes','cases/minimal_coupons/definition.json','cases/minimal_coupons/provenance.json',
                 'outputs/minimal_coupon_v1/manifest.json','docs/COMSOL_H0_RESULTS.md','docs/COMSOL_TASK.md',
                 'docs/MINIMAL_COUPON_RESULTS.md','scripts/coupon_common.py','scripts/import_comsol.py',
                 'scripts/run_comsol_h0.py','scripts/comsol/H0Thermal.java','scripts/restore_h0_evidence_bytes.py',
                 'scripts/package_comsol_h0.py','verification/provenance_validation.json']:
        names.add(ROOT/name)
    # Preserve diagnostics from failed/superseded attempts, without mislabelled or unsolved models.
    for attempt in (ROOT/'outputs/comsol_h0').iterdir():
        if attempt.is_dir() and attempt!=result and (attempt/'run_status.json').exists():
            names.update(p for p in attempt.rglob('*') if p.is_file() and p.suffix in {'.log','.json'})
    names.update((ROOT/'outputs/comsol_h0/byte_recovery').glob('*/restoration.json'))
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sorted(names)}
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(names):
            z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
        z.writestr('FILE_SHA256.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        import hashlib
        for name,sha in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=sha:
                raise ValueError('Packaged bytes mismatch: '+name)
    write_json(ROOT/'verification/comsol_imports/h0_z16/deliverable.json',
               {'packaged_at':datetime.now(timezone.utc).isoformat(),'file':str(target.relative_to(ROOT)).replace('\\','/'),
                'sha256':digest(target),'bytes':target.stat().st_size,'file_count':len(manifest),
                'zip_crc_and_sha256':'pass','final_result_directory':str(result.relative_to(ROOT)).replace('\\','/')})
    print(json.dumps({'package':str(target),'sha256':digest(target),'files':len(manifest)},indent=2))


if __name__=='__main__':
    main()
