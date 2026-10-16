#!/usr/bin/env python3
"""Validate local provenance data only; never import or run a physics solver."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def local_file(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Path leaves this project: " + relative)
    if not path.is_file():
        raise ValueError("Missing local file: " + relative)
    return path


def main():
    errors = []
    manifest = read_json("references/import_manifest.json")
    for item in manifest["files"]:
        try:
            actual = hashlib.sha256(local_file(item["snapshot"]).read_bytes()).hexdigest()
            if actual != item["sha256"]:
                errors.append("Snapshot hash mismatch: " + item["snapshot"])
        except ValueError as exc:
            errors.append(str(exc))

    catalog = read_json("sources/catalog.json")["sources"]
    sources = {s["source_id"]: s for s in catalog}
    if len(sources) != len(catalog):
        errors.append("Duplicate source IDs")
    for source in catalog:
        if source.get("local_snapshot"):
            try:
                actual = hashlib.sha256(local_file(source["local_snapshot"]).read_bytes()).hexdigest()
                if actual != source["sha256"]:
                    errors.append("Source hash mismatch: " + source["source_id"])
            except ValueError as exc:
                errors.append(str(exc))

    registry = read_json("parameters/registry.json")
    params = registry["parameters"]
    ids = {p["parameter_id"] for p in params}
    if len(ids) != len(params):
        errors.append("Duplicate parameter IDs")
    gaps = read_json("parameters/gap_registry.json")["gaps"]
    if {g["gap_id"] for g in gaps} != {"G%02d" % i for i in range(1, 37)}:
        errors.append("Original 36 audit gaps not preserved")
    gap_ids = {g["gap_id"] for g in gaps}
    candidates = 0
    for param in params:
        if not set(param["gap_ids"]).issubset(gap_ids):
            errors.append("Unknown gap reference: " + param["parameter_id"])
        if param["selected_value"] is not None or param["adoption_status"] != "not_adopted":
            errors.append("This preparation-stage registry must not silently adopt values: " + param["parameter_id"])
        if not param["candidates"] and param["evidence_status"] != "missing":
            errors.append("Missing candidate mislabeled as available: " + param["parameter_id"])
        for candidate in param["candidates"]:
            candidates += 1
            source_id = candidate["source_id"]
            if source_id not in sources:
                errors.append("Unknown source: " + source_id)
                continue
            source = sources[source_id]
            if candidate["value"] is None:
                errors.append("Candidate has no value: " + param["parameter_id"])
            if not candidate["applicability"]:
                errors.append("Candidate lacks applicability: " + param["parameter_id"])
            if candidate.get("line"):
                try:
                    lines = local_file(source["local_snapshot"]).read_text(encoding="utf-8").splitlines()
                    line = candidate["line"]
                    if line < 1 or line > len(lines):
                        errors.append("Citation line out of range: " + param["parameter_id"])
                    elif candidate.get("anchor") and candidate["anchor"] not in lines[line - 1]:
                        errors.append("Citation anchor mismatch: " + param["parameter_id"])
                except (ValueError, KeyError) as exc:
                    errors.append(str(exc))
            if candidate["source_assertion"] == "derived" and not candidate.get("derivation"):
                errors.append("Derived value lacks derivation: " + param["parameter_id"])
    for gap in gaps:
        if not set(gap["candidate_parameter_ids"]).issubset(ids):
            errors.append("Gap points to unknown parameter: " + gap["gap_id"])

    case = read_json("cases/tap_multigpu_research_definition.json")
    local_file(case["layout_reference"])
    if case["solver_ready"] or case["mechanical_stress_pa"] is not None:
        errors.append("Draft case must not claim a solved/ready physical model")
    if any(v is not None for v in case["required_physics"].values()):
        errors.append("Unexpected adoption in draft physical definition")
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "scope": "snapshot_and_provenance_integrity_only",
        "snapshot_count": len(manifest["files"]),
        "source_count": len(sources),
        "parameter_count": len(params),
        "candidate_count": candidates,
        "audit_gap_count": len(gaps),
        "adopted_parameter_count": sum(p["selected_value"] is not None for p in params),
        "research_model_status": "missing_parameters",
        "research_etm_solved": False,
        "mechanical_stress_pa": None,
        "optimization_started": False,
        "errors": errors,
    }
    output = ROOT / "verification/provenance_validation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
