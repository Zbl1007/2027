"""Shared input, geometry and result contracts. Contains no numerical PDE solver."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "cases/minimal_coupons/definition.json"
PACKAGE = ROOT / "outputs/minimal_coupon_v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def write_csv(path, fields, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_definition():
    data = json.loads(DEFINITION.read_text())
    if data["fidelity"] != "synthetic_fixture" or data["research_parameter_adoption"]:
        raise ValueError("Only the separately scoped synthetic fixture is supported")
    for mat in data["materials"].values():
        for key in ["k_w_mk", "cv_j_m3k", "young_pa", "cte_per_k"]:
            if mat[key] is None or not math.isfinite(mat[key]) or mat[key] <= 0:
                raise ValueError("Missing/invalid material " + key)
        if not -1 < mat["poisson"] < 0.5:
            raise ValueError("Invalid Poisson ratio")
    return data


def rectangles(data, variant):
    """Disjoint 2-D partition: four matrix + four liner + one copper rectangles."""
    d = data["h1"]
    lx, ly, _ = d["size_m"]
    cx, cy = d["centres_m"][variant]
    a = d["core_side_m"] / 2
    b = a + d["liner_width_m"]
    raw = [
        ("si_bottom", "silicon", 0, 0, lx, cy-b),
        ("si_top", "silicon", 0, cy+b, lx, ly-cy-b),
        ("si_left", "silicon", 0, cy-b, cx-b, 2*b),
        ("si_right", "silicon", cx+b, cy-b, lx-cx-b, 2*b),
        ("ox_bottom", "silica", cx-b, cy-b, 2*b, b-a),
        ("ox_top", "silica", cx-b, cy+a, 2*b, b-a),
        ("ox_left", "silica", cx-b, cy-a, b-a, 2*a),
        ("ox_right", "silica", cx+a, cy-a, b-a, 2*a),
        ("cu_core", "copper", cx-a, cy-a, 2*a, 2*a),
    ]
    return [dict(zip(["id", "material", "x_m", "y_m", "width_m", "depth_m"], r)) for r in raw]


def validate_regions(regions, size):
    lx, ly, _ = size
    area = 0.0
    for i, a in enumerate(regions):
        x, y, w, h = [a[k] for k in ["x_m", "y_m", "width_m", "depth_m"]]
        if not all(math.isfinite(v) for v in [x, y, w, h]) or min(w, h) <= 0:
            raise ValueError("Invalid region dimensions")
        if x < 0 or y < 0 or x+w > lx+1e-15 or y+h > ly+1e-15:
            raise ValueError("Region outside domain")
        area += w*h
        for b in regions[i+1:]:
            dx = min(x+w, b["x_m"]+b["width_m"]) - max(x, b["x_m"])
            dy = min(y+h, b["y_m"]+b["depth_m"]) - max(y, b["y_m"])
            if dx > 1e-15 and dy > 1e-15:
                raise ValueError("Overlapping material regions")
    if not math.isclose(area, lx*ly, rel_tol=1e-12):
        raise ValueError("Material coverage has gaps")


def analytic_h0(data, z):
    """Closed-form reference, not a replacement thermal solver; z=0 insulated."""
    lx, ly, length = data["h0"]["size_m"]
    q = data["h0"]["power_w"] / (lx*ly*length)
    k = data["materials"]["silicon"]["k_w_mk"]
    bc = data["thermal_boundary"]
    return bc["ambient_k"] + q*length/bc["top_h_w_m2k"] + q*(length**2-z**2)/(2*k)


def read_field(path):
    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("Empty field")
    seen = set()
    for row in rows:
        for k in ["x_m", "y_m", "z_m", "temperature_k"]:
            row[k] = float(row[k])
            if not math.isfinite(row[k]):
                raise ValueError("Non-finite " + k)
        key = tuple(row[k] for k in ["x_m", "y_m", "z_m"])
        if key in seen:
            raise ValueError("Duplicate sample coordinate")
        seen.add(key)
        if row["temperature_k"] <= 0:
            raise ValueError("Non-positive absolute temperature")
    return rows


def compare_samples(reference, incoming, tolerance):
    """Require the exact exported sample sequence; prevent missing/extra/shifted data."""
    if len(reference) != len(incoming):
        raise ValueError("Sample count mismatch")
    errors = []
    for a, b in zip(reference, incoming):
        if any(abs(float(a[k])-float(b[k])) > tolerance for k in ["x_m", "y_m", "z_m"]):
            raise ValueError("Coordinate/order mismatch (SI meters required)")
        errors.append(abs(float(a["temperature_k"])-float(b["temperature_k"])))
    return {"max_abs_error_k": max(errors), "rmse_k": math.sqrt(sum(e*e for e in errors)/len(errors)), "sample_count": len(errors)}
