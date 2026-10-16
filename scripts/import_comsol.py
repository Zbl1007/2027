#!/usr/bin/env python3
"""Fail-closed import of externally solved COMSOL thermal fields (stdlib only)."""
import argparse
import csv
import io
import json
import math
from itertools import product
from pathlib import Path
from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, read_field, compare_samples, write_csv, write_json


def read_comsol(path, reference, tolerance):
    """Accept canonical CSV or COMSOL 4-column x,y,z,T export with % comments."""
    lines=[line.strip() for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith(("%","#"))]
    if lines and lines[0].split(",")==["x_m","y_m","z_m","temperature_k"]:
        rows=list(csv.DictReader(io.StringIO("\n".join(lines))))
    else:
        rows=[]
        for line in lines:
            values=line.replace(","," ").split()
            if len(values)!=4:
                raise ValueError("Export must have exactly x,y,z,T columns in m and K")
            rows.append(dict(zip(["x_m","y_m","z_m","temperature_k"],values)))
    for row in rows:
        for key in row:
            row[key]=float(row[key])
            if not math.isfinite(row[key]): raise ValueError("Non-finite field value")
        if row["temperature_k"]<=0: raise ValueError("Temperature must be absolute K")
    # Match coordinates within the declared tolerance, including harmless export rounding.
    # No interpolation, extrapolation, or silently dropped points.
    if len(rows)!=len(reference): raise ValueError("Sample count mismatch")
    if len({tuple(r[k] for k in ["x_m","y_m","z_m"]) for r in rows})!=len(rows):
        raise ValueError("Duplicate coordinate")
    keys=["x_m","y_m","z_m"]
    buckets={}
    for i,r in enumerate(rows):
        key=tuple(round(r[k]/tolerance) for k in keys)
        buckets.setdefault(key,[]).append(i)
    ordered=[]; used=set()
    for r in reference:
        key=tuple(round(float(r[k])/tolerance) for k in keys)
        candidates=[]
        for offset in product((-1,0,1),repeat=3):
            for i in buckets.get(tuple(k+d for k,d in zip(key,offset)),[]):
                if all(abs(rows[i][k]-float(r[k]))<=tolerance for k in keys): candidates.append(i)
        if len(candidates)!=1 or candidates[0] in used: raise ValueError("Coordinate mismatch or ambiguous duplicate (SI meters required)")
        used.add(candidates[0]); ordered.append(rows[candidates[0]])
    compare_samples(reference,ordered,tolerance)
    return ordered


def positive(value, name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
        raise ValueError("Missing/invalid positive value: "+name)
    return value


def evaluate(case_id, result_dir):
    data=load_definition(); a=data["acceptance"]; folder=PACKAGE/case_id
    contract_path=folder/"contract.json"
    c=json.loads(contract_path.read_text()); m=json.loads((result_dir/"metadata.json").read_text())
    manifest=json.loads((PACKAGE/"manifest.json").read_text())
    expected={e["case_id"]:e["contract_sha256"] for e in manifest["cases"]}
    if expected.get(case_id)!=digest(contract_path) or c["case_id"]!=case_id: raise ValueError("Unknown/changed local contract")
    if c["definition_sha256"]!=digest(DEFINITION): raise ValueError("Stale local case definition")
    if m.get("case_id")!=case_id or m.get("contract_sha256")!=digest(contract_path): raise ValueError("Case/contract mismatch")
    if m.get("status")!="solved" or m.get("solver")!="COMSOL" or m.get("result_kind")!="external_solver_output":
        raise ValueError("Real completed COMSOL solver output required")
    for key in ["solver_version","solved_at","operator","notes"]:
        if not isinstance(m.get(key),str) or not m[key].strip(): raise ValueError("Missing metadata: "+key)
    if m.get("units")!={"coordinates":"m","temperature":"K","power":"W"}: raise ValueError("Units must be m/K/W")
    evidence={}
    for role in ["model","solver_log"]:
        item=m.get("evidence",{}).get(role,{})
        name=item.get("file")
        if not isinstance(name,str) or Path(name).name!=name: raise ValueError("Evidence must be a local filename")
        path=result_dir/name
        if not path.is_file() or path.stat().st_size==0 or digest(path)!=item.get("sha256"):
            raise ValueError("Missing/changed evidence: "+role)
        if role=="model" and path.suffix.lower()!=".mph": raise ValueError("Supply the solved .mph model")
        evidence[role]={"file":name,"sha256":digest(path)}
    base_dof=positive(m.get("base_mesh_dof"),"base_mesh_dof")
    if positive(m.get("refined_mesh_dof"),"refined_mesh_dof")<=base_dof: raise ValueError("Refinement must increase DOF")
    qin=positive(m.get("integrated_source_w"),"integrated_source_w")
    qout=positive(m.get("integrated_top_outward_heat_w"),"integrated_top_outward_heat_w")
    ref=read_field(folder/"3dice_field.csv")
    # Hash local solver evidence so a comparison cannot silently use edited temperatures.
    local=json.loads((folder/"3dice_result.json").read_text())
    for name,sha in local["artifacts_sha256"].items():
        if digest(folder/name)!=sha: raise ValueError("Changed local 3D-ICE evidence: "+name)
    base=read_comsol(result_dir/"temperature_base.csv",ref,a["coordinate_tolerance_m"])
    fine=read_comsol(result_dir/"temperature_refined.csv",ref,a["coordinate_tolerance_m"])
    comparison=compare_samples(ref,fine,a["coordinate_tolerance_m"])
    mesh=compare_samples(base,fine,a["coordinate_tolerance_m"])
    errors={"source_relative_error":abs(qin-c["total_power_w"])/c["total_power_w"],"balance_relative_error":abs(qout-qin)/qin}
    accepted=comparison["max_abs_error_k"]<=a["external_temperature_max_error_k"] and mesh["max_abs_error_k"]<=a["comsol_mesh_change_max_k"] and max(errors.values())<=a["external_power_relative_error"]
    report={"case_id":case_id,"status":"thermal_comparison_pass" if accepted else "thermal_comparison_fail",
        "scope":"this_thermal_fixture_and_sampling_only; not_all_cases_not_mechanics_not_TAP",
        "contract_sha256":digest(contract_path),"metadata_sha256":digest(result_dir/"metadata.json"),"evidence":evidence,
        "comparison":comparison,"comsol_mesh_change":mesh,"mesh_change_limit_k":a["comsol_mesh_change_max_k"],**errors,
        "comsol_fields_sha256":{name:digest(result_dir/name) for name in ["temperature_base.csv","temperature_refined.csv"]},
        "mechanical_stress_pa":None,"requires_human_model_review":True}
    return report, fine


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id"); parser.add_argument("result_dir",type=Path)
    args=parser.parse_args()
    if Path(args.case_id).name!=args.case_id: parser.error("case_id must be a plain case name")
    out=ROOT/"verification/comsol_imports"/args.case_id
    try:
        report,field=evaluate(args.case_id,args.result_dir)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        write_json(out/"comparison.json",{"case_id":args.case_id,"status":"import_rejected","reason":str(exc),"mechanical_stress_pa":None})
        raise SystemExit("Import rejected: "+str(exc))
    write_json(out/"comparison.json",report)
    write_csv(out/"comsol_field.csv",["x_m","y_m","z_m","temperature_k"],field)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"]!="thermal_comparison_pass": raise SystemExit(1)


if __name__=="__main__": main()
