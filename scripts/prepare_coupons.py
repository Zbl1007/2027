#!/usr/bin/env python3
"""Generate identical continuous-geometry contracts for 3D-ICE and COMSOL."""
import shutil
from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, rectangles, validate_regions, write_csv, write_json


def prepare(data, case_id, size, regions, nxy, nz, q):
    folder = PACKAGE / case_id
    folder.mkdir(parents=True, exist_ok=True)
    validate_regions(regions, size)
    height = size[2]/nz
    volume = {m: sum(r["width_m"]*r["depth_m"]*size[2] for r in regions if r["material"] == m) for m in data["materials"]}
    power = q*volume["silicon"]
    flp = []
    for r in regions:
        imposed_power = q*r["width_m"]*r["depth_m"]*height if r["material"] == "silicon" else 0.0
        flp.append(f'{r["id"]}:\n position {r["x_m"]*1e6:.17g}, {r["y_m"]*1e6:.17g};\n dimension {r["width_m"]*1e6:.17g}, {r["depth_m"]*1e6:.17g};\n material {r["material"]};\n discretization {nxy}, {nxy};\n power values {imposed_power:.17g};\n')
    (folder / "source.flp").write_text("\n".join(flp))
    lines = []
    for m in sorted(set(r["material"] for r in regions)):
        prop = data["materials"][m]
        lines.append(f'material {m}:\n thermal conductivity {prop["k_w_mk"]*1e-6:.17g};\n volumetric heat capacity {prop["cv_j_m3k"]*1e-18:.17g};\n')
    bc = data["thermal_boundary"]
    lines += [f'top heat sink:\n heat transfer coefficient {bc["top_h_w_m2k"]*1e-12:.17g};\n temperature {bc["ambient_k"]:.17g};',
              f'dimensions:\n chip length {size[0]*1e6:.17g}, width {size[1]*1e6:.17g};\n cell length {size[0]*1e6:.17g}, width {size[1]*1e6:.17g};\n non-uniform true;',
              f'die slice:\n source {height*1e6:.17g} silicon;', 'stack:']
    # Stack text is TOP to BOTTOM. Our canonical z is BOTTOM to TOP.
    lines += [f' die layer{i} slice floorplan "source.flp";' for i in reversed(range(nz))]
    lines += [f'solver:\n steady;\n initial temperature {bc["ambient_k"]:.17g};\n numofcores 1;', 'output:\n T3d("temperature.vtk", final);']
    (folder / "case.stk").write_text("\n".join(lines)+"\n")
    contract = {"case_id": case_id, "fidelity": "synthetic_fixture", "definition_sha256": digest(DEFINITION),
        "size_m": size, "regions": regions, "region_volumes_m3": volume, "total_power_w": power,
        "q_silicon_w_m3": q, "xy_subdivisions_per_region": nxy, "z_cells": nz,
        "expected_cells": len(regions)*nxy*nxy*nz, "thermal_boundary": bc,
        "three_d_ice_inputs": {p: digest(folder/p) for p in ["case.stk", "source.flp"]},
        "mechanical_stress_pa": None, "comsol_status": "pending_external_solver"}
    write_json(folder/"contract.json", contract)
    write_csv(folder/"regions_si.csv", ["id","material","x_m","y_m","width_m","depth_m"], regions)
    return {"case_id": case_id, "contract_sha256": digest(folder/"contract.json")}


def main():
    data = load_definition()
    PACKAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEFINITION, PACKAGE/"definition.json")
    cases=[]
    size=data["h0"]["size_m"]
    regions=[{"id":"body", "material":"silicon", "x_m":0.0,"y_m":0.0,"width_m":size[0],"depth_m":size[1]}]
    q=data["h0"]["power_w"]/(size[0]*size[1]*size[2])
    for nz in data["h0"]["z_cells"]:
        cases.append(prepare(data, f"h0_z{nz}", size, regions, data["h0"]["xy_subdivisions"], nz, q))
    for variant in data["h1"]["centres_m"]:
        for nxy,nz in data["h1"]["mesh_levels"]:
            cases.append(prepare(data, f"h1_{variant}_xy{nxy}_z{nz}", data["h1"]["size_m"], rectangles(data, variant), nxy, nz, data["h1"]["q_silicon_w_m3"]))
    write_json(PACKAGE/"manifest.json", {"family":data["case_family"], "cases":cases, "definition_sha256":digest(DEFINITION), "thermal_status":"prepared_not_run", "mechanical_stress_pa":None})
    print(f"Prepared {len(cases)} fixtures: {PACKAGE}")


if __name__ == "__main__":
    main()
