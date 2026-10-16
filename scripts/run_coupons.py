#!/usr/bin/env python3
"""Run existing 3D-ICE; validate/export its cell fields without solving a PDE."""
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, analytic_h0, read_field, write_csv, write_json


def parse_vtk(path, contract):
    tokens = path.read_text().split()
    if "ASCII" not in tokens or "UNSTRUCTURED_GRID" not in tokens:
        raise ValueError("Expected ASCII unstructured VTK")
    i=tokens.index("POINTS"); np=int(tokens[i+1]); start=i+3
    coords=list(map(float,tokens[start:start+3*np]))
    points=[coords[j:j+3] for j in range(0,len(coords),3)]
    i=tokens.index("CELLS"); nc=int(tokens[i+1]); start=i+3
    if nc != contract["expected_cells"] or np != 8*nc:
        raise ValueError("Cell count differs from contract")
    cells=[]
    for _ in range(nc):
        if tokens[start] != "8":
            raise ValueError("Only eight-vertex hexes are supported")
        cells.append([points[int(j)] for j in tokens[start+1:start+9]]); start+=9
    i=tokens.index("CELL_TYPES")
    if int(tokens[i+1]) != nc or set(tokens[i+2:i+2+nc]) != {"12"}:
        raise ValueError("Not all cells are VTK_HEXAHEDRON")
    i=tokens.index("CELL_DATA")
    if int(tokens[i+1]) != nc:
        raise ValueError("Temperature field count mismatch")
    i=tokens.index("Temperature",i)
    if tokens[i+3:i+5] != ["LOOKUP_TABLE","default"]:
        raise ValueError("Unexpected temperature scalar format")
    temps=list(map(float,tokens[i+5:i+5+nc]))
    rows=[]; volumes={m:0.0 for m in contract["region_volumes_m3"]}
    for vertices,temperature in zip(cells,temps):
        bounds=[(min(p[d] for p in vertices)*1e-6,max(p[d] for p in vertices)*1e-6) for d in range(3)]
        x,y,z=[(a+b)/2 for a,b in bounds]
        volume=math.prod(b-a for a,b in bounds)
        if volume<=0 or not math.isfinite(temperature) or temperature<=0:
            raise ValueError("Invalid solver cell")
        if any(a < -1e-15 or b > lim+1e-15 for (a,b),lim in zip(bounds,contract["size_m"])):
            raise ValueError("Solver geometry out of domain")
        matches=[r for r in contract["regions"] if r["x_m"]<x<r["x_m"]+r["width_m"] and r["y_m"]<y<r["y_m"]+r["depth_m"]]
        if len(matches)!=1:
            raise ValueError("Cell cannot be assigned uniquely to material")
        r=matches[0]; m=r["material"]
        if bounds[0][0]<r["x_m"]-1e-15 or bounds[0][1]>r["x_m"]+r["width_m"]+1e-15 or bounds[1][0]<r["y_m"]-1e-15 or bounds[1][1]>r["y_m"]+r["depth_m"]+1e-15:
            raise ValueError("Cell crosses material boundary")
        volumes[m]+=volume
        rows.append({"x_m":x,"y_m":y,"z_m":z,"temperature_k":temperature,"volume_m3":volume,"material":m,"region":r["id"]})
    for m,v in volumes.items():
        if not math.isclose(v,contract["region_volumes_m3"][m],rel_tol=1e-8,abs_tol=1e-30):
            raise ValueError("Output volume mismatch: "+m)
    rows.sort(key=lambda r:(r["z_m"],r["y_m"],r["x_m"]))
    return rows


def main():
    data=load_definition()
    build_path=ROOT/"verification/three_d_ice_build/build.json"
    build=json.loads(build_path.read_text())
    binary=ROOT/build["binary"]
    if digest(binary)!=build["binary_sha256"]:
        raise ValueError("Executable differs from build evidence")
    manifest=json.loads((PACKAGE/"manifest.json").read_text())
    if manifest["definition_sha256"]!=digest(DEFINITION):
        raise ValueError("Stale package; run prepare_coupons.py")
    results=[]
    for entry in manifest["cases"]:
        folder=PACKAGE/entry["case_id"]
        contract=json.loads((folder/"contract.json").read_text())
        if entry["contract_sha256"]!=digest(folder/"contract.json"):
            raise ValueError("Contract hash mismatch")
        for name,sha in contract["three_d_ice_inputs"].items():
            if digest(folder/name)!=sha:
                raise ValueError("Changed solver input: "+name)
        vtk=folder/"temperature.vtk"
        if vtk.exists(): vtk.unlink()  # never accept a stale successful solver output
        env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
        proc=subprocess.run([str(binary),"case.stk"],cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        (folder/"3dice.log").write_text(proc.stdout)
        if proc.returncode or not vtk.exists():
            raise RuntimeError(f"3D-ICE failed: {folder}; see 3dice.log")
        rows=parse_vtk(vtk,contract)
        write_csv(folder/"3dice_field.csv",list(rows[0]),rows)
        read_field(folder/"3dice_field.csv")
        # COMSOL data-export interpolation coordinates: 3 columns, meters, no header.
        (folder/"sample_points_m.txt").write_text("".join(" ".join(f'{r[k]:.17g}' for k in ["x_m","y_m","z_m"])+"\n" for r in rows))
        volume=sum(r["volume_m3"] for r in rows)
        dz=contract["size_m"][2]/contract["z_cells"]
        top_z=contract["size_m"][2]-dz/2
        bc=contract["thermal_boundary"]
        # Reconstruct boundary flux from the exported solution; this is not a solve.
        qout=sum((r["volume_m3"]/dz)/(1/bc["top_h_w_m2k"]+dz/(2*data["materials"][r["material"]]["k_w_mk"]))*(r["temperature_k"]-bc["ambient_k"])
                 for r in rows if abs(r["z_m"]-top_z)<1e-14)
        balance=abs(qout-contract["total_power_w"])/contract["total_power_w"]
        if balance>1e-7: raise ValueError("Exported field does not balance prescribed heat")
        result={"case_id":entry["case_id"],"status":"three_d_ice_solved_comsol_pending",
            "contract_sha256":entry["contract_sha256"],"build_sha256":digest(build_path),"returncode":proc.returncode,
            "cell_count":len(rows),"min_temperature_k":min(r["temperature_k"] for r in rows),
            "max_temperature_k":max(r["temperature_k"] for r in rows),
            "volume_mean_temperature_k":sum(r["temperature_k"]*r["volume_m3"] for r in rows)/volume,
            "total_power_w":contract["total_power_w"],"reconstructed_top_outward_heat_w":qout,"heat_balance_relative_error":balance,"comsol_stress_pa":None,
            "artifacts_sha256":{p:digest(folder/p) for p in ["temperature.vtk","3dice_field.csv","sample_points_m.txt","3dice.log"]}}
        if entry["case_id"].startswith("h0_"):
            comparisons=[{"z_m":r["z_m"],"three_d_ice_k":r["temperature_k"],"analytic_k":analytic_h0(data,r["z_m"]),"abs_error_k":abs(r["temperature_k"]-analytic_h0(data,r["z_m"]))} for r in rows]
            write_csv(folder/"analytic_comparison.csv",list(comparisons[0]),comparisons)
            result["analytic_max_error_k"]=max(r["abs_error_k"] for r in comparisons)
        write_json(folder/"3dice_result.json",result)
        results.append(result)
        print(entry["case_id"],len(rows),f'Tmax={result["max_temperature_k"]:.9f} K',flush=True)
    h0=[r for r in results if "analytic_max_error_k" in r]
    ratios=[a["analytic_max_error_k"]/b["analytic_max_error_k"] for a,b in zip(h0,h0[1:])]
    a=data["acceptance"]
    passed=h0[-1]["analytic_max_error_k"]<=a["h0_finest_max_error_k"] and all(a["h0_error_ratio_min"]<=r<=a["h0_error_ratio_max"] for r in ratios)
    summary={"checked_at":datetime.now(timezone.utc).isoformat(),"scope":"synthetic_thermal_fixtures_only",
        "h0_analytic_pass":passed,"h0_error_ratios":ratios,"cases":results,
        "comsol_validation":"pending_external_solver","mechanical_stress_pa":None,"tap_solver_ready":False,
        "known_backend_limitations":["Nonuniform lowest SOURCE/SOLID layer uses full cell height for internal vertical half-resistance; observed bottom-centre excess error documented in docs/MINIMAL_COUPON_RESULTS.md. No equation patch applied.","H1 mesh changes exceed position differences; no position-effect claim."]}
    write_json(ROOT/"verification/minimal_coupon_validation.json",summary)
    write_json(PACKAGE/"3dice_summary.json",summary)
    if not passed:
        raise RuntimeError("H0 analytical verification failed")
    print("H0 analytic verification PASS; H1 external reference and all mechanics pending.")


if __name__ == "__main__":
    main()
