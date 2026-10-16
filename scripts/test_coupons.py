#!/usr/bin/env python3
"""Focused adapter tests. Synthetic parser inputs are never saved as solver evidence."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from coupon_common import ROOT, PACKAGE, DEFINITION, digest, load_definition, rectangles, validate_regions, analytic_h0, compare_samples, read_field, write_json
from import_comsol import read_comsol, evaluate
from run_coupons import parse_vtk


class Coupons(unittest.TestCase):
    def test_material_provenance_and_capacities(self):
        d=load_definition(); sources=json.loads((ROOT/"cases/minimal_coupons/provenance.json").read_text())["sources"]
        for m in d["materials"].values():
            for k in ["thermal_source","mechanical_source","density_source"]: self.assertIn(m[k],sources)
            self.assertAlmostEqual(m["rho_kg_m3"]*m["cp_j_kgk"],m["cv_j_m3k"])
        self.assertEqual(d["mechanical"]["solved_stress_pa"],None)

    def test_shift_preserves_physical_volumes_and_power(self):
        d=load_definition(); allvol=[]
        for v in ["centered","shifted"]:
            rs=rectangles(d,v); validate_regions(rs,d["h1"]["size_m"])
            volumes={m:sum(r["width_m"]*r["depth_m"]*d["h1"]["size_m"][2] for r in rs if r["material"]==m) for m in d["materials"]}
            allvol.append(volumes)
            self.assertTrue(math.isclose(volumes["silicon"]*5e9,0.0012958,rel_tol=1e-12))
            self.assertTrue(math.isclose(volumes["copper"],1.1e-14,rel_tol=1e-12))
        for m in allvol[0]: self.assertTrue(math.isclose(allvol[0][m],allvol[1][m],rel_tol=1e-12))

    def test_geometry_rejects_overlap_and_gaps(self):
        d=load_definition(); rs=rectangles(d,"centered")
        with self.assertRaises(ValueError): validate_regions(rs+rs[:1],d["h1"]["size_m"])
        with self.assertRaises(ValueError): validate_regions(rs[:-1],d["h1"]["size_m"])

    def test_closed_form_boundaries(self):
        d=load_definition()
        self.assertAlmostEqual(analytic_h0(d,1e-4),305)
        self.assertAlmostEqual(analytic_h0(d,0),305.1923076923077)

    def test_real_vtk_contract_and_heat_balance(self):
        manifest=json.loads((PACKAGE/"manifest.json").read_text())
        self.assertEqual(manifest["definition_sha256"],digest(DEFINITION))
        for e in manifest["cases"]:
            p=PACKAGE/e["case_id"]; c=json.loads((p/"contract.json").read_text())
            self.assertEqual(e["contract_sha256"],digest(p/"contract.json"))
            rows=parse_vtk(p/"temperature.vtk",c)
            self.assertEqual(len(rows),c["expected_cells"])
            result=json.loads((p/"3dice_result.json").read_text())
            self.assertLess(result["heat_balance_relative_error"],1e-7)

    def test_comsol_coordinate_matching_and_rejections(self):
        ref=read_field(PACKAGE/"h0_z4/3dice_field.csv"); tol=1e-10
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"parser_input.csv"
            # Data generated for format checking only; no COMSOL solver metadata or results.
            lines=[','.join(str(r[k]) for k in ["x_m","y_m","z_m","temperature_k"]) for r in ref]
            p.write_text('% parser unit test\n'+'\n'.join(reversed(lines)))
            self.assertEqual(compare_samples(ref,read_comsol(p,ref,tol),tol)["max_abs_error_k"],0)
            for text in ['\n'.join(lines[:-1]),'\n'.join(lines[:-1]+[lines[0]]),'\n'.join(lines).replace('305.', 'nan305.')]:
                p.write_text(text)
                with self.assertRaises(ValueError): read_comsol(p,ref,tol)
            p.write_text('\n'.join(' '.join(str(r[k]*1e6) for k in ["x_m","y_m","z_m"])+f' {r["temperature_k"]}' for r in ref))
            with self.assertRaises(ValueError): read_comsol(p,ref,tol)

    def test_unrun_or_wrong_contract_cannot_be_imported(self):
        name="h0_z16"; contract=digest(PACKAGE/name/"contract.json")
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write_json(p/"metadata.json",{"case_id":name,"contract_sha256":contract,"status":"not_run"})
            with self.assertRaisesRegex(ValueError,"completed COMSOL"): evaluate(name,p)
            write_json(p/"metadata.json",{"case_id":name,"contract_sha256":"wrong","status":"solved"})
            with self.assertRaisesRegex(ValueError,"contract mismatch"): evaluate(name,p)

    def test_tap_adoption_untouched(self):
        registry=json.loads((ROOT/"parameters/registry.json").read_text())
        self.assertTrue(all(p["selected_value"] is None for p in registry["parameters"]))
        case=json.loads((ROOT/"cases/tap_multigpu_research_definition.json").read_text())
        self.assertFalse(case["solver_ready"])
        self.assertIsNone(case["mechanical_stress_pa"])


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Coupons))
    write_json(ROOT/"verification/coupon_adapter_tests.json",{"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"pass":result.wasSuccessful(),"scope":"adapter_and_real_3dice_artifacts; no_COMSOL_solve"})
    raise SystemExit(0 if result.wasSuccessful() else 1)
