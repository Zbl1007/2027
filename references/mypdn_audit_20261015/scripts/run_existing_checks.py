"""P0: run a bounded selection of existing tests; never run an optimizer."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "evidence"
GROUPS = {
    "data_dc": [
        "tests/unit/test_tap_50x50_cases.py",
        "tests/cases",
        "tests/unit/test_config_units.py",
        "tests/unit/test_schema_v2.py",
        "tests/unit/test_prepared_circuit.py",
        "tests/unit/test_dc_activation.py",
        "tests/golden/test_dc_builder_analytic.py",
        "tests/golden/test_multi_ground_dc_builder.py",
        "tests/golden/test_site_option_dc_v2.py",
    ],
    "thermal_et": [
        "tests/unit/test_thermal_formulas.py",
        "tests/unit/test_thermal_mapping.py",
        "tests/unit/test_thermal_v2_types.py",
        "tests/unit/test_thermal_v2_selected_macros.py",
        "tests/unit/test_thermal_v2_mapping.py",
        "tests/unit/test_electrothermal_mapping.py",
        "tests/golden/test_thermal_analytic.py",
        "tests/golden/test_thermal_v2_analytic.py",
        "tests/golden/test_electrothermal_fixed_point.py",
        "tests/golden/test_electrothermal_v2.py",
    ],
    "physics_hard": [
        "tests/unit/test_tiv_macro_physics_v2.py::test_effective_geometry_derives_all_lumped_macro_physics",
        "tests/unit/test_tiv_macro_physics_v2.py::test_effective_geometry_rejects_nonphysical_copper_occupancy",
        "tests/unit/test_hard_placement_v2.py",
        "tests/golden/test_fresh_hard_constraints_v2.py::test_repeated_calls_are_fresh_rebuilds_with_stable_constraints",
        "tests/golden/test_fresh_hard_constraints_v2.py::test_soft_and_stale_hard_placements_are_rejected",
        "tests/golden/test_fresh_hard_constraints_v2.py::test_fresh_hard_constraints_match_across_backends[scipy]",
        "tests/unit/test_calibration_v2_reference.py",
    ],
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    for name, paths in GROUPS.items():
        command = [sys.executable, "-m", "pytest", *paths, "-q", "-ra", "-p", "no:cacheprovider", f"--junitxml={OUT / (name + '.xml')}"]
        start = time.monotonic()
        with (OUT / (name + ".log")).open("w") as log:
            try:
                completed = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = 124
                log.write("\nP0 timeout: 180 seconds; stopped.\n")
        records.append({"group": name, "command": command, "exit_code": code, "duration_seconds": round(time.monotonic() - start, 3), "log": name + ".log", "junit": name + ".xml"})
        (OUT / "test_runs.json").write_text(json.dumps(records, indent=2) + "\n")
        print(name, "exit", code, "seconds", records[-1]["duration_seconds"], flush=True)
    return int(any(row["exit_code"] != 0 for row in records))


if __name__ == "__main__":
    raise SystemExit(main())
