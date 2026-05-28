#!/usr/bin/env python3
from pathlib import Path
from nested_kernel import NestedKernel, NestedEvent

DATA = Path("./nested_data")
kernel = NestedKernel(DATA / "nested_state.json")

root = kernel.boot_root("root")

# Build geometry:
# root
# ├── UR
# ├── L
# └── DL
#     └── DL
#         └── DL
kernel.spawn_child("root", "UR", "root.UR", {"role": "upper_right_start"})
kernel.spawn_child("root", "L", "root.L", {"role": "left_pass"})
kernel.spawn_child("root", "DL", "root.DL", {"role": "down_left_first"})
kernel.spawn_child("root.DL", "DL", "root.DL.DL", {"role": "down_left_again"})
kernel.spawn_child("root.DL.DL", "DL", "root.DL.DL.DL", {"role": "down_left_again_again"})

kernel.apply_event("root.UR", NestedEvent(
    source="demo",
    intent="mutate",
    payload={"delta": 0.00000001, "state_delta": {"probe": "UR first read"}}
))

kernel.apply_event("root.DL.DL.DL", NestedEvent(
    source="demo",
    intent="assimilate",
    payload={"state_delta": {"wisdom": "deepest down-left residue"}}
))

wind = kernel.wind("root")
unwind = kernel.unwind("root")

print("Traversal order:")
for i, cid in enumerate(unwind["order"], 1):
    print(f"{i:02d}. {cid}")

print("\nGlobal root:")
print(unwind["global_root"])

print("\nUnwind trail:")
for item in unwind["trail"]:
    print(item["cell_id"], item["position"], item["local_root"][:16], item["state"])
