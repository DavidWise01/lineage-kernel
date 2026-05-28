#!/usr/bin/env python3
"""
lineage_kernel.py — PCK SelfSeed Lineage Propagator

A bounded seed runtime for source-preserving, responsible propagation.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Literal
import hashlib, json, time, uuid, copy

Decision = Literal["ALLOW", "DENY", "QUARANTINE", "DEFER"]

AXIOMS = [
    "No state persists without an admissible transition.",
    "No propagation without source lineage.",
    "No public child seed may contain private parent data.",
    "A child may mutate only within delta-bound limits.",
    "Bad memory may be transformed into wisdom residue, then pruned.",
]

def now() -> float:
    return time.time()

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        return json.loads(path.read_text())
    return default

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str))

@dataclass
class SourceLineage:
    source_type: str
    source_name: str
    source_role: str = "originator"
    source_uri: Optional[str] = None
    source_hash: Optional[str] = None
    rights_note: str = "lineage retained; no ownership erased"

    def normalized(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source_id"] = sha256_obj(data)
        return data

@dataclass
class Seed:
    source: Dict[str, Any]
    payload: Dict[str, Any]
    parent_seed: Optional[str] = None
    delta: float = 0.00000001
    visibility: str = "private"
    wisdom: list = field(default_factory=list)
    created: float = field(default_factory=now)
    rollback: Optional[Dict[str, Any]] = None
    seed_id: Optional[str] = None
    root: Optional[str] = None

    def finalize(self) -> "Seed":
        body = asdict(self)
        body.pop("seed_id", None)
        body.pop("root", None)
        self.root = sha256_obj(body)
        self.seed_id = "seed_" + self.root[:24]
        return self

    def to_dict(self) -> Dict[str, Any]:
        if not self.root or not self.seed_id:
            self.finalize()
        return asdict(self)

class LineageKernel:
    def __init__(self, data_dir: Path, policy_path: Optional[Path] = None):
        self.data_dir = data_dir
        self.policy = load_json(policy_path or Path("seed_policy.json"), self.default_policy())
        self.events_path = data_dir / "lineage_events.jsonl"
        self.witness_path = data_dir / "witness.json"
        self.root_seed_path = data_dir / "root_seed.json"
        self.child_seed_path = data_dir / "child_seed.json"

    @staticmethod
    def default_policy() -> Dict[str, Any]:
        return {
            "delta_limit": 0.00000001,
            "allow_publication": False,
            "require_source_lineage": True,
            "require_parent_root": True,
            "strip_private_payload": True,
            "require_rollback": True,
            "critical_private_keys": ["private_key", "secret", "token", "password", "api_key", "raw_private_memory"]
        }

    def append_event(self, event: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        event["timestamp"] = now()
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    def create_root_seed(self, source: SourceLineage, payload: Dict[str, Any], visibility: str = "private") -> Dict[str, Any]:
        seed = Seed(
            source=source.normalized(),
            payload=payload,
            parent_seed=None,
            visibility=visibility,
            rollback={"available": True, "type": "root_snapshot"}
        ).finalize()
        data = seed.to_dict()
        write_json(self.root_seed_path, data)
        self.append_event({"type": "root_seed_created", "seed_id": data["seed_id"], "root": data["root"], "source": data["source"]})
        self.update_witness("root_created", data)
        return data

    def strip_private(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = copy.deepcopy(payload)
        private_keys = set(self.policy.get("critical_private_keys", []))

        def clean_obj(obj):
            if isinstance(obj, dict):
                return {k: clean_obj(v) for k, v in obj.items() if k not in private_keys and not k.startswith("_private")}
            if isinstance(obj, list):
                return [clean_obj(x) for x in obj]
            return obj

        return clean_obj(cleaned)

    def propose_child_seed(self, parent_seed: Dict[str, Any], mutation: Dict[str, Any], visibility: str = "shared") -> Dict[str, Any]:
        parent_payload = parent_seed.get("payload", {})
        child_payload = copy.deepcopy(parent_payload)
        child_payload.update(mutation.get("payload_delta", {}))

        if self.policy.get("strip_private_payload", True):
            child_payload = self.strip_private(child_payload)

        child = Seed(
            source=parent_seed["source"],
            payload=child_payload,
            parent_seed=parent_seed["seed_id"],
            delta=float(mutation.get("delta", 0.00000001)),
            visibility=visibility,
            wisdom=parent_seed.get("wisdom", []),
            rollback={"available": True, "parent_seed": parent_seed["seed_id"], "parent_root": parent_seed["root"]}
        ).finalize()

        data = child.to_dict()
        write_json(self.child_seed_path, data)
        self.append_event({"type": "child_seed_proposed", "parent": parent_seed["seed_id"], "child": data["seed_id"]})
        return data

    def evaluate_propagation(self, parent_seed: Dict[str, Any], child_seed: Dict[str, Any]) -> Dict[str, Any]:
        checks = {
            "source_lineage_present": bool(child_seed.get("source", {}).get("source_id")),
            "parent_root_present": bool(parent_seed.get("root")) and child_seed.get("parent_seed") == parent_seed.get("seed_id"),
            "delta_within_limit": abs(float(child_seed.get("delta", 0))) <= float(self.policy.get("delta_limit", 0.00000001)),
            "rollback_available": bool(child_seed.get("rollback", {}).get("available")),
            "private_data_removed": self.private_data_removed(child_seed.get("payload", {})),
            "child_hash_valid": child_seed.get("root") == sha256_obj({k:v for k,v in child_seed.items() if k not in ("seed_id", "root")})
        }

        critical = all(checks.values())

        if not checks["source_lineage_present"]:
            decision, reason = "DENY", "missing_source_lineage"
        elif not checks["parent_root_present"]:
            decision, reason = "DENY", "missing_or_invalid_parent_root"
        elif not checks["private_data_removed"]:
            decision, reason = "QUARANTINE", "private_data_detected"
        elif not checks["delta_within_limit"]:
            decision, reason = "QUARANTINE", "delta_exceeds_limit"
        elif not critical:
            decision, reason = "DEFER", "noncritical_check_pending"
        elif child_seed.get("visibility") == "public" and not self.policy.get("allow_publication", False):
            decision, reason = "DEFER", "publication_valve_closed"
        else:
            decision, reason = "ALLOW", "responsible_propagation_admissible"

        record = {
            "type": "propagation_evaluated",
            "decision": decision,
            "reason": reason,
            "checks": checks,
            "parent_seed": parent_seed.get("seed_id"),
            "child_seed": child_seed.get("seed_id")
        }
        self.append_event(record)
        self.update_witness("propagation_evaluated", record)
        return record

    def private_data_removed(self, payload: Dict[str, Any]) -> bool:
        private_keys = set(self.policy.get("critical_private_keys", []))

        def scan(obj) -> bool:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in private_keys or k.startswith("_private"):
                        return False
                    if not scan(v):
                        return False
            elif isinstance(obj, list):
                return all(scan(x) for x in obj)
            return True

        return scan(payload)

    def assimilate_bad_memory(self, seed: Dict[str, Any], raw_ref: str, residue: str) -> Dict[str, Any]:
        seed = copy.deepcopy(seed)
        seed.setdefault("wisdom", []).append({
            "from": raw_ref,
            "residue": residue,
            "pruned_raw": True,
            "timestamp": now()
        })
        # Re-root after assimilation.
        body = {k:v for k,v in seed.items() if k not in ("seed_id", "root")}
        seed["root"] = sha256_obj(body)
        seed["seed_id"] = "seed_" + seed["root"][:24]
        self.append_event({"type": "bad_memory_assimilated", "seed_id": seed["seed_id"], "from": raw_ref, "residue": residue})
        return seed

    def update_witness(self, reason: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        previous = load_json(self.witness_path, {"current_root": "0"*64, "events": 0})
        witness = {
            "reason": reason,
            "previous_root": previous.get("current_root", "0"*64),
            "object_hash": sha256_obj(obj),
            "timestamp": now(),
            "axioms": AXIOMS,
        }
        witness["current_root"] = sha256_obj(witness)
        witness["events"] = int(previous.get("events", 0)) + 1
        write_json(self.witness_path, witness)
        return witness
