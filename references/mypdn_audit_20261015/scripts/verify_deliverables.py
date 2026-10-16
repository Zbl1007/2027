"""Validate P0 report/evidence integrity, not the validity of a TAP ETM model."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parents[1]
EVIDENCE = AUDIT / "evidence"


def main():
    baseline = json.loads((EVIDENCE / "input_hashes.json").read_text())
    changed = []
    for name, expected in baseline["files"].items():
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(name)
    runs = json.loads((EVIDENCE / "test_runs.json").read_text())
    summaries = []
    for row in runs:
        tree = ET.parse(EVIDENCE / row["junit"])
        suites = list(tree.getroot().iter("testsuite"))
        counts = {key: sum(int(s.get(key, "0")) for s in suites) for key in ["tests", "failures", "errors", "skipped"]}
        summaries.append(dict(group=row["group"], exit_code=row["exit_code"], **counts))
    with (AUDIT / "ETM_PARAMETER_GAPS.csv").open(encoding="utf-8-sig", newline="") as f:
        gaps = list(csv.DictReader(f))
    reports = ["README.md", "ETM_IMPLEMENTATION_AUDIT.md", "ETM_CASE_PHYSICAL_SUMMARY.md", "ETM_REUSE_AND_CHANGE_PLAN.md", "ETM_VALIDATION_RECORD.md"]
    probes = json.loads((EVIDENCE / "numerical_probes.json").read_text())
    compiler = json.loads((EVIDENCE / "compiler_probe.json").read_text())
    tests_ok = len(runs) == 3 and all(r["exit_code"] == 0 and r["tests"] > 0 and r["failures"] == r["errors"] == r["skipped"] == 0 for r in summaries)
    probes_ok = set(probes) == {"power_accounting", "one_macro_move", "v1_relaxed_stop", "signed_boundary_flux", "backend_smoke"} and compiler["load_compiled_artifacts_succeeded"]
    docs_ok = all((AUDIT / name).is_file() and (AUDIT / name).stat().st_size > 100 for name in reports) and len(gaps) == 36 and len({r['gap_id'] for r in gaps}) == 36 and all(all(v and v.strip() for v in row.values()) for row in gaps)
    result = {
        "scope": "P0 audit deliverable integrity; not TAP model acceptance",
        "selected_existing_tests_passed": tests_ok,
        "selected_test_total": sum(r["tests"] for r in summaries),
        "test_summaries": summaries,
        "numerical_probes_complete": bool(probes_ok),
        "audited_inputs_unchanged": not changed,
        "changed_inputs": changed,
        "reports_and_gap_table_valid": bool(docs_ok),
        "gap_rows": len(gaps),
        "research_etm_solved": False,
        "mechanical_stress_pa": None,
        "optimization_started": False,
    }
    result["status"] = "pass" if tests_ok and probes_ok and docs_ok and not changed else "fail"
    (EVIDENCE / "deliverable_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
