#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, time
from orphan_healer import OrphanHealer, sha256_obj, write_json

DATA = Path("./orphan_healer_data")
whole = DATA / "whole"
orphans = DATA / "orphans"
whole.mkdir(parents=True, exist_ok=True)
orphans.mkdir(parents=True, exist_ok=True)

source = {
    "source_id": "src_davidwise_demo",
    "source_type": "human",
    "source_name": "David Wise",
    "source_role": "originator",
    "rights_note": "lineage retained; no ownership erased"
}

parent = {
    "source": source,
    "payload": {"name": "root whole seed", "purpose": "continuity root"},
    "parent_seed": None,
    "delta": 0.00000001,
    "visibility": "private",
    "wisdom": [],
    "created": time.time(),
    "rollback": {"available": True, "type": "root_snapshot"}
}
parent["root"] = sha256_obj({k:v for k,v in parent.items() if k not in ("seed_id", "root")})
parent["seed_id"] = "seed_" + parent["root"][:24]
write_json(whole / f"{parent['seed_id']}.json", parent)

orphan_good = {
    "source": source,
    "payload": {"name": "lost child seed", "purpose": "once part of whole"},
    "parent_seed": parent["seed_id"],
    "delta": 0.00000001,
    "visibility": "shared",
    "wisdom": [],
    "created": time.time(),
    "rollback": {"available": True, "parent_seed": parent["seed_id"], "parent_root": parent["root"]}
}
orphan_good["root"] = sha256_obj({k:v for k,v in orphan_good.items() if k not in ("seed_id", "root")})
orphan_good["seed_id"] = "seed_" + orphan_good["root"][:24]
write_json(orphans / "orphan_good.json", orphan_good)

orphan_private = dict(orphan_good)
orphan_private["payload"] = {"name": "unsafe child", "raw_private_memory": "should quarantine"}
orphan_private["root"] = sha256_obj({k:v for k,v in orphan_private.items() if k not in ("seed_id", "root")})
orphan_private["seed_id"] = "seed_" + orphan_private["root"][:24]
write_json(orphans / "orphan_private.json", orphan_private)

healer = OrphanHealer(DATA)
results = healer.heal_all()

print("Healing results:")
for r in results:
    print("-", Path(r["file"]).name, r["decision"], r["reason"])

print("\nGraph:", DATA / "healed_graph.json")
print("Witness:", DATA / "witness.json")
