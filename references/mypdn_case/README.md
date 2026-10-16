# TAP-Derived 50x50 Cases

These files preserve the local workload, chiplet geometry, power, frequency
metadata, and relative floorplan from `data/ascend910.yaml`,
`data/micro150.yaml`, and `data/multigpu.yaml` while placing each design on a
50 mm by 50 mm interposer.

The layouts use a rigid translation snapped to the 0.2 mm electrical grid.
No chiplet is independently moved, resized, or rotated. The declared thermal
grid and TIV candidate pitch are both 1 mm.

The files are explicit, derived layouts rather than TAP simulated-annealing
outputs. TAP connection matrices remain bandwidth metadata and must not be
converted into DC load current. Frequency values come from the local legacy
YAML files and are not claimed as TAP benchmark fields.

The original files under `data/` remain unchanged because historical migration
and comparison tests depend on their original extents and coordinates.
