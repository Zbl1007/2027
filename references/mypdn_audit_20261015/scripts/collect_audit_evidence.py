"""Read current inputs and exercise existing tiny fixtures, without an optimizer.

All numerical probes here are synthetic_fixture diagnostics, not TAP results.
No electrical, thermal, or mechanical solver is implemented in this script.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parents[1] / "evidence"

import numpy as np
import scipy
from scipy import sparse
import torch
import yaml
import pytest
import matplotlib
import networkx


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def environment():
    commands = ["comsol", "comsolbatch", "3D-ICE", "3d-ice", "ccx", "ElmerSolver", "FreeFem++"]
    packages = ["mph", "dolfin", "dolfinx", "sfepy", "meshio", "gmsh"]
    matches = {}
    for base in [Path('/Applications'), Path.home()/'Applications', Path('/opt'), Path('/usr/local')]:
        matches[str(base)] = sorted(str(p) for p in base.iterdir() if 'comsol' in p.name.lower()) if base.is_dir() else []
    return {
        "python": sys.executable, "python_version": sys.version,
        "platform": platform.platform(), "machine": platform.machine(),
        "packages": {m.__name__: m.__version__ for m in [np, scipy, torch, yaml, pytest, matplotlib, networkx]},
        "cuda_available": torch.cuda.is_available(),
        "backend_commands": {name: shutil.which(name) for name in commands},
        "mechanics_packages": {name: importlib.util.find_spec(name) is not None for name in packages},
        "comsol_install_directory_matches": matches,
        "comsol_license_status": "not_verified_no_local_executable_found",
        "scope": "local host PATH and listed installation roots; no remote host or license checkout",
    }


def case_summary():
    from cowos_l_tiv.config import load_design
    path = ROOT / 'data/tap_50x50/multigpu.yaml'
    raw = yaml.safe_load(path.read_text())
    try:
        load_design(path)
        loader = {"accepted": True}
    except Exception as exc:
        loader = {"accepted": False, "exception": type(exc).__name__, "message": str(exc)}
    return {
        "source": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "raw": raw, "nominal_power_w": sum(c['power'] for c in raw['chiplets']),
        "package_technology": None, "frozen_via_layout": None,
        "power_via_count": None, "ground_via_count": None, "via_diameter_m": None,
        "stress_pa": None, "status": "missing_parameters_and_backend",
        "load_design_probe": loader,
    }


def compiler_probe(work):
    from tests.cases.test_case_bundle import _write_minimal_bundle
    from cowos_l_tiv.cases.compiler import compile_case, load_compiled_artifacts
    case = _write_minimal_bundle(work / 'tiny_case')
    config = yaml.safe_load((ROOT/'configs/case_compilation/blackwell_b2.yaml').read_text())
    config.update(name='P0_synthetic_fixture', analysis_extent_mm={'width': 1.0, 'height': 0.8})
    for key in ['electrical_grid', 'thermal_grid']:
        config[key] = {'pitch_x_mm': 0.2, 'pitch_y_mm': 0.2, 'columns': 5, 'rows': 4}
    config_path = work/'compile_fixture.yaml'
    config_path.write_text(yaml.safe_dump(config))
    result = compile_case(case, config_path, work/'compiled')
    second = compile_case(case, config_path, work/'compiled')
    load_compiled_artifacts(work/'compiled')
    for name in ['compiled.manifest.json','normalized_case.json','mapping_summary.json','thermal_instance_power.json']:
        shutil.copyfile(work/'compiled'/name, OUT/('fixture_'+name))
    return {'fidelity': 'synthetic_fixture', 'cache_miss_first': not result.cache_hit,
            'cache_hit_second': second.cache_hit, 'hashes_equal': result.generated_design_hash == second.generated_design_hash,
            'load_compiled_artifacts_succeeded': True, 'compiler_grid_cells': 20}


def numerical_probes(work):
    from tests.step17_test_helpers import make_step17_fixture
    from cowos_l_tiv.candidates import make_hard_placement_v2
    from cowos_l_tiv.analysis.dc_v2 import solve_dc_v2
    from cowos_l_tiv.thermal_v2 import build_thermal_v2, solve_thermal_v2
    from tests.phase_b5_test_helpers import make_thermal_design
    from tests.phase_b3_test_helpers import SYNTHETIC_PROVENANCE
    from cowos_l_tiv.thermal_v2 import BoundaryConditionSpec
    from tests.phase4_test_helpers import load_electrothermal_design, hard_placement
    from cowos_l_tiv.analysis import solve_electrothermal, solve_dc, solve_thermal
    from cowos_l_tiv.builders import build_dc_circuit, build_thermal_circuit
    from cowos_l_tiv.analysis.electrothermal import thermal_build_snapshot_with_joule
    from cowos_l_tiv.mapping.electrothermal import precompute_electrothermal_mapping

    _, compilation, placement, thermal, overlap, spec, evaluator, evaluation = make_step17_fixture()
    r = evaluation.result
    balance = r.dc.global_power_balance
    power = {
        'fidelity': 'synthetic_fixture', 'mock': False, 'converged': r.converged,
        'current_contract_feasible': evaluation.report.feasible,
        'source_power_w': balance.source_delivered_power_w,
        'actual_load_power_w': balance.load_power_w,
        'pdn_loss_w': balance.network_joule_power_w,
        'die_heat_w': r.thermal.chip_power_w,
        'joule_heat_w': r.thermal.joule_power_w,
        'thermal_injected_w': r.thermal.thermal_injected_power_w,
        'dc_balance_residual_w': balance.power_residual_w,
        'thermal_balance_residual_w': r.thermal.thermal_residual_w,
        'die_heat_minus_actual_iv_w': r.thermal.chip_power_w - balance.load_power_w,
        'thermal_input_minus_electrical_source_w': r.thermal.thermal_injected_power_w - balance.source_delivered_power_w,
    }
    fixed = tuple(o.id for o in compilation.space.options if o.fixed)
    optional = [o.id for o in compilation.space.options if not o.fixed]
    a = evaluator(make_hard_placement_v2(compilation.space, (*fixed, optional[0])))
    b = evaluator(make_hard_placement_v2(compilation.space, (*fixed, optional[-1])))
    def endpoints(ev):
        return [(x.kind, asdict(x.u), asdict(x.v)) for x in ev.dc_build.branch_registry.records if x.kind.startswith('tiv_option')]
    move = {
        'fidelity': 'synthetic_fixture', 'mock': False, 'search_or_optimization': False,
        'selected_a': list(a.placement.selected_option_ids), 'selected_b': list(b.placement.selected_option_ids),
        'physical_macro_count_a': a.thermal_build.selected_physical_macro_count,
        'physical_macro_count_b': b.thermal_build.selected_physical_macro_count,
        'same_macro_geometry': True, 'fingerprint_changed': a.input_fingerprint != b.input_fingerprint,
        'dc_endpoints_changed': endpoints(a) != endpoints(b),
        'thermal_overlap_changed': a.thermal_build.tiv_option_cell_weights != b.thermal_build.tiv_option_cell_weights,
        'joule_mapping_changed': (a.mappings.joule.matrix != b.mappings.joule.matrix).nnz > 0,
        'dc_max_voltage_delta_v': float(torch.max(torch.abs(a.result.dc.node_voltage_v-b.result.dc.node_voltage_v))),
        'max_temperature_field_delta_k': float(torch.max(torch.abs(a.result.thermal.temperature_k-b.result.thermal.temperature_k))),
    }
    v1 = load_electrothermal_design(work/'v1', tolerance_k=1e-4, relaxation=1e-8, max_iterations=1, max_retries=0)
    state = hard_placement(v1)
    actual = solve_electrothermal(v1, state, mode='hard')
    dc_build = build_dc_circuit(v1, state, mode='hard')
    t_build = build_thermal_circuit(v1, state, mode='hard')
    maps = precompute_electrothermal_mapping(dc_build, t_build)
    dc = solve_dc(dc_build, backend='scipy')
    q = maps.map_joule_power(dc.branch_joule_power_w).reshape(t_build.result_plan.grid_shape_zyx)
    raw_t = solve_thermal(thermal_build_snapshot_with_joule(t_build, q), backend='scipy')
    v1_probe = {
        'fidelity': 'synthetic_fixture', 'mock': False,
        'relaxation': 1e-8, 'tolerance_k': 1e-4,
        'reported_converged': actual.converged,
        'reported_relaxed_step_k': actual.residual_history_k[-1],
        'raw_fixed_point_residual_from_initial_k': float(torch.max(torch.abs(raw_t.temperature_k-v1.thermal_boundary.ambient_temperature_k))),
        'returned_vs_raw_heat_solution_delta_k': float(torch.max(torch.abs(raw_t.temperature_k-actual.thermal.temperature_k))),
    }
    mixed = make_thermal_design(nx=1,powers=(0.0,))
    mixed = replace(mixed, boundary=replace(mixed.boundary,
        top=BoundaryConditionSpec('fixed_temperature',temperature_k=308.15,provenance=SYNTHETIC_PROVENANCE),
        bottom=BoundaryConditionSpec('fixed_temperature',temperature_k=288.15,provenance=SYNTHETIC_PROVENANCE)))
    mixed_result = solve_thermal_v2(build_thermal_v2(mixed,sparse.csr_matrix([[1.0]])))
    heat_flux = {'fidelity':'synthetic_fixture','mock':False,'die_heat_w':0.0,
        'top_temperature_k':308.15,'bottom_temperature_k':288.15,
        'reported_boundary_flow_w':mixed_result.boundary_heat_flow_w,
        'reported_residual_w':mixed_result.thermal_residual_w,
        'expected_net_boundary_flow_w_for_source_free_steady_state':0.0}
    backends = {}
    for name in ['scipy','pardiso','cudss']:
        try:
            solved = solve_dc_v2(evaluation.dc_build,backend=name)
            backends[name]={'status':'solved_synthetic_fixture','power_residual_w':solved.global_power_balance.power_residual_w}
        except Exception as exc:
            backends[name]={'status':'unavailable','error_type':type(exc).__name__,'message':str(exc)}
    return {'power_accounting':power,'one_macro_move':move,'v1_relaxed_stop':v1_probe,'signed_boundary_flux':heat_flux,'backend_smoke':backends}


def main():
    save('environment.json',environment())
    save('case_summary.json',case_summary())
    with tempfile.TemporaryDirectory(prefix='etm-p0-synthetic-') as tmp:
        work=Path(tmp)
        save('compiler_probe.json',compiler_probe(work))
        save('numerical_probes.json',numerical_probes(work))
    print('Audit probes completed; all numerical outputs are synthetic_fixture.')


if __name__ == '__main__':
    main()
