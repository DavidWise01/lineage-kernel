#!/usr/bin/env python3
from pathlib import Path
import json
from lineage_kernel import LineageKernel, SourceLineage

DATA = Path("./selfseed_data")
kernel = LineageKernel(DATA, Path("seed_policy.json"))

source = SourceLineage(
    source_type="human",
    source_name="David Wise",
    source_role="originator",
    source_uri="https://github.com/DavidWise01",
    rights_note="source lineage retained; artist/originator attribution preserved"
)

root_payload = {
    "name": "PCK SelfSeed",
    "purpose": "standalone seed that contains itself and propagates responsibly",
    "raw_private_memory": "THIS SHOULD NOT PROPAGATE",
    "nested": {
        "kernel": "PCK",
        "delta": 0.00000001,
        "loops": ["heal", "align", "learn", "propagate"]
    }
}

root = kernel.create_root_seed(source, root_payload, visibility="private")
print("root seed:", root["seed_id"])

child = kernel.propose_child_seed(
    root,
    mutation={
        "delta": 0.00000001,
        "payload_delta": {
            "generation": 1,
            "propagation_note": "responsible child seed; private data stripped"
        }
    },
    visibility="shared"
)
print("child seed:", child["seed_id"])

decision = kernel.evaluate_propagation(root, child)
print("decision:", decision["decision"], "-", decision["reason"])
print("checks:", json.dumps(decision["checks"], indent=2))

print("witness written:", DATA / "witness.json")
