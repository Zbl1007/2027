#!/usr/bin/env python3
"""Generate COMSOL parameter/import templates and a portable, solver-free ZIP."""
import json
import shutil
import zipfile
from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, write_csv, write_json


def main():
    data=load_definition()
    manifest=json.loads((PACKAGE/"manifest.json").read_text())
    if manifest["definition_sha256"]!=digest(DEFINITION): raise ValueError("Regenerate stale cases first")
    mats=[]
    for name,p in data["materials"].items():
        mats.append({"material":name,**{k:p[k] for k in ["k_w_mk","rho_kg_m3","cp_j_kgk","cv_j_m3k","young_pa","poisson","cte_per_k"]}})
    write_csv(PACKAGE/"materials_si.csv",list(mats[0]),mats)
    props=[("k","k_w_mk","W/(m*K)"),("rho","rho_kg_m3","kg/m^3"),("cp","cp_j_kgk","J/(kg*K)"),("E","young_pa","Pa"),("nu","poisson",None),("alpha","cte_per_k","1/K")]
    for entry in manifest["cases"]:
        folder=PACKAGE/entry["case_id"]
        if digest(folder/"contract.json")!=entry["contract_sha256"]: raise ValueError("Modified contract")
        c=json.loads((folder/"contract.json").read_text())
        result=json.loads((folder/"3dice_result.json").read_text())
        if result["contract_sha256"]!=entry["contract_sha256"]: raise ValueError("Stale solver result")
        for name,sha in result["artifacts_sha256"].items():
            if digest(folder/name)!=sha: raise ValueError("Changed result: "+name)
        params=[(axis,lim,"m") for axis,lim in zip(["Lx","Ly","Lz"],c["size_m"])]
        params += [("qSi",c["q_silicon_w_m3"],"W/m^3"),("hTop",data["thermal_boundary"]["top_h_w_m2k"],"W/(m^2*K)"),("Tamb",300,"K"),("Tref",data["mechanical"]["reference_k"],"K"),("dTtest",data["mechanical"]["uniform_delta_k"],"K")]
        for name,prefix in [("silicon","si"),("copper","cu"),("silica","ox")]:
            params += [(prefix+"_"+short,data["materials"][name][key],unit) for short,key,unit in props]
        (folder/"comsol_parameters.txt").write_text("".join(f'{name}\t{value:.17g}'+(f'[{unit}]' if unit else '')+'\n' for name,value,unit in params))
        template={"case_id":entry["case_id"],"contract_sha256":entry["contract_sha256"],
            "status":"not_run","solver":"COMSOL","result_kind":"external_solver_output",
            "solver_version":None,"solved_at":None,"operator":None,"notes":None,
            "units":{"coordinates":"m","temperature":"K","power":"W"},
            "base_mesh_dof":None,"refined_mesh_dof":None,"integrated_source_w":None,"integrated_top_outward_heat_w":None,
            "evidence":{"model":{"file":None,"sha256":None},"solver_log":{"file":None,"sha256":None}}}
        write_json(folder/"return_metadata_template.json",template)
    write_json(PACKAGE/"mechanical_return_template.json",{
        "status":"not_run","solver":"COMSOL","solver_version":None,"definition_sha256":digest(DEFINITION),
        "units":{"displacement":"m","stress":"Pa","reaction":"N"},
        "m0a":{"far_x_u_m":None,"far_y_v_m":None,"far_z_w_m":None,"max_von_mises_pa":None},
        "m0b":{"volume_mean_sigma_zz_pa":None,"top_reaction_z_n":None,"far_x_u_m":None},
        "model_files":[],"solver_logs":[],"constraint_screenshots":[],"review_status":"pending_real_solver_and_manual_review"})
    # Copy only reproducibility artifacts, never a fake .mph or machine-specific executable.
    files=[p for p in PACKAGE.rglob("*") if p.is_file()]
    files += [DEFINITION, ROOT/"cases/minimal_coupons/provenance.json",
        ROOT/"docs/COMSOL_TASK.md",ROOT/"docs/MINIMAL_COUPON_SPEC.md",ROOT/"docs/MINIMAL_COUPON_RESULTS.md",
        ROOT/"scripts/coupon_common.py",ROOT/"scripts/import_comsol.py",
        ROOT/"sources/three_d_ice.lock.json",ROOT/"patches/3dice-vtk-precision.patch",
        ROOT/"verification/minimal_coupon_validation.json",ROOT/"verification/three_d_ice_build/build.json",
        ROOT/"verification/three_d_ice_build/build.log"]
    files=sorted(set(files))
    top="3dice_comsol_minimal_v1"
    delivery=ROOT/"deliverables"; delivery.mkdir(exist_ok=True)
    archive=delivery/(top+".zip")
    checksums={str(p.relative_to(ROOT)):digest(p) for p in files}
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(top+"/START_HERE.md","# 先做 H0\n\n请打开 [COMSOL 操作任务单](docs/COMSOL_TASK.md)，从“本次先做什么”开始。\n\n本包已有真实 3D-ICE 结果，COMSOL 需在你的电脑上按步骤建模运行。没有预生成 .mph。参数是独立验证算例定义，不是 TAP 已采用参数。\n\n优先目录：outputs/minimal_coupon_v1/h0_z16/\n")
        for p in files: z.write(p,top+"/"+str(p.relative_to(ROOT)))
        z.writestr(top+"/SHA256SUMS.json",json.dumps(checksums,indent=2)+"\n")
    write_json(delivery/(top+".json"),{"file":archive.name,"sha256":digest(archive),"files":len(files)+2,
        "comsol_status":"pending_external_solver","includes_solved_mph":False})
    print(str(archive))


if __name__=="__main__": main()
