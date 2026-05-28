#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import hashlib, json, time, copy

Decision = Literal["REATTACH", "QUARANTINE", "ASSIMILATE", "REJECT", "DEFER"]

def now() -> float:
    return time.time()

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str))

class OrphanHealer:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.whole_dir = data_dir / "whole"
        self.orphan_dir = data_dir / "orphans"
        self.events_path = data_dir / "stitch_events.jsonl"
        self.graph_path = data_dir / "healed_graph.json"
        self.witness_path = data_dir / "witness.json"
        self.private_keys = {"private_key", "secret", "token", "password", "api_key", "raw_private_memory"}

    def append_event(self, event: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        event["timestamp"] = now()
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    def load_whole(self) -> List[Dict[str, Any]]:
        return [s for s in (read_json(p) for p in self.whole_dir.glob("*.json")) if s]

    def scan_orphans(self) -> List[Path]:
        self.orphan_dir.mkdir(parents=True, exist_ok=True)
        return sorted(self.orphan_dir.glob("*.json"))

    def strip_private(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self.strip_private(v) for k, v in obj.items()
                    if k not in self.private_keys and not k.startswith("_private")}
        if isinstance(obj, list):
            return [self.strip_private(x) for x in obj]
        return obj

    def has_private(self, obj: Any) -> bool:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in self.private_keys or k.startswith("_private"):
                    return True
                if self.has_private(v):
                    return True
        elif isinstance(obj, list):
            return any(self.has_private(x) for x in obj)
        return False

    def recompute_seed_root(self, seed: Dict[str, Any]) -> str:
        body = {k: v for k, v in seed.items() if k not in ("seed_id", "root")}
        return sha256_obj(body)

    def relationship_score(self, orphan: Dict[str, Any], whole: List[Dict[str, Any]]) -> Dict[str, Any]:
        best = {"score": 0.0, "parent": None, "signals": []}
        orphan_source = orphan.get("source", {}).get("source_id")
        orphan_parent = orphan.get("parent_seed")
        rollback_parent = orphan.get("rollback", {}).get("parent_seed")
        rollback_root = orphan.get("rollback", {}).get("parent_root")

        for seed in whole:
            score = 0.0
            signals = []
            if orphan_source and orphan_source == seed.get("source", {}).get("source_id"):
                score += 0.30; signals.append("source_id_match")
            if orphan_parent and orphan_parent == seed.get("seed_id"):
                score += 0.30; signals.append("parent_seed_match")
            if rollback_parent and rollback_parent == seed.get("seed_id"):
                score += 0.20; signals.append("rollback_parent_match")
            if rollback_root and rollback_root == seed.get("root"):
                score += 0.20; signals.append("rollback_root_match")
            if abs(float(orphan.get("delta", 0.00000001))) <= 0.00000001:
                score += 0.10; signals.append("delta_compatible")
            if seed.get("source") and orphan.get("source"):
                if seed["source"].get("source_name") == orphan["source"].get("source_name"):
                    score += 0.10; signals.append("source_name_match")

            if score > best["score"]:
                best = {"score": min(score, 1.0), "parent": seed.get("seed_id"), "signals": signals}
        return best

    def evaluate_orphan(self, orphan: Dict[str, Any], whole: List[Dict[str, Any]]) -> Dict[str, Any]:
        source_ok = bool(orphan.get("source", {}).get("source_id"))
        root_valid = orphan.get("root") == self.recompute_seed_root(orphan)
        private_present = self.has_private(orphan.get("payload", {}))
        relation = self.relationship_score(orphan, whole)

        if not source_ok:
            decision, reason = "REJECT", "missing_source_lineage"
        elif private_present:
            decision, reason = "QUARANTINE", "private_payload_present"
        elif not root_valid:
            decision, reason = "QUARANTINE", "root_hash_invalid"
        elif relation["score"] >= 0.70:
            decision, reason = "REATTACH", "lineage_relation_strong"
        elif relation["score"] >= 0.40:
            decision, reason = "DEFER", "lineage_relation_partial"
        elif orphan.get("wisdom"):
            decision, reason = "ASSIMILATE", "wisdom_present_but_lineage_weak"
        else:
            decision, reason = "REJECT", "lineage_relation_insufficient"

        return {
            "decision": decision,
            "reason": reason,
            "checks": {
                "source_ok": source_ok,
                "root_valid": root_valid,
                "private_present": private_present,
                "relationship": relation
            }
        }

    def heal_orphan_file(self, path: Path) -> Dict[str, Any]:
        whole = self.load_whole()
        orphan = read_json(path)
        if not orphan:
            rec = {"file": str(path), "decision": "REJECT", "reason": "unparseable_json"}
            self.append_event(rec)
            return rec

        # sanitize copy for possible reattachment
        clean_orphan = copy.deepcopy(orphan)
        clean_orphan["payload"] = self.strip_private(clean_orphan.get("payload", {}))

        evaluation = self.evaluate_orphan(clean_orphan, whole)
        decision = evaluation["decision"]

        rec = {
            "file": str(path),
            "orphan_seed": clean_orphan.get("seed_id"),
            **evaluation
        }

        if decision == "REATTACH":
            out = self.whole_dir / f"{clean_orphan.get('seed_id','reattached')}.json"
            write_json(out, clean_orphan)
            rec["reattached_path"] = str(out)
        elif decision == "ASSIMILATE":
            residue = {
                "from_orphan": clean_orphan.get("seed_id"),
                "source": clean_orphan.get("source"),
                "wisdom": clean_orphan.get("wisdom", []),
                "assimilated_at": now(),
            }
            out = self.whole_dir / f"wisdom_{sha256_obj(residue)[:16]}.json"
            write_json(out, residue)
            rec["assimilated_path"] = str(out)
        elif decision == "QUARANTINE":
            qdir = self.data_dir / "quarantine"
            qdir.mkdir(exist_ok=True)
            out = qdir / path.name
            write_json(out, clean_orphan)
            rec["quarantine_path"] = str(out)

        self.append_event(rec)
        self.update_graph()
        self.update_witness(rec)
        return rec

    def heal_all(self) -> List[Dict[str, Any]]:
        return [self.heal_orphan_file(p) for p in self.scan_orphans()]

    def update_graph(self) -> Dict[str, Any]:
        whole = self.load_whole()
        nodes = []
        edges = []
        for seed in whole:
            sid = seed.get("seed_id") or sha256_obj(seed)[:16]
            nodes.append({
                "id": sid,
                "root": seed.get("root"),
                "source": seed.get("source", {}).get("source_name"),
                "type": "seed" if "payload" in seed else "wisdom"
            })
            if seed.get("parent_seed"):
                edges.append({"from": seed["parent_seed"], "to": sid, "type": "parent"})
            if seed.get("rollback", {}).get("parent_seed"):
                edges.append({"from": seed["rollback"]["parent_seed"], "to": sid, "type": "rollback"})
        graph = {
            "updated": now(),
            "nodes": nodes,
            "edges": edges,
            "graph_root": sha256_obj({"nodes": nodes, "edges": edges})
        }
        write_json(self.graph_path, graph)
        return graph

    def update_witness(self, last_event: Dict[str, Any]) -> Dict[str, Any]:
        prev = read_json(self.witness_path) or {"current_root": "0"*64, "events": 0}
        graph = read_json(self.graph_path) or {}
        witness = {
            "previous_root": prev.get("current_root", "0"*64),
            "last_event_hash": sha256_obj(last_event),
            "graph_root": graph.get("graph_root"),
            "events": int(prev.get("events", 0)) + 1,
            "timestamp": now(),
            "law": "No orphan rejoins the whole without lineage proof and safety validation."
        }
        witness["current_root"] = sha256_obj(witness)
        write_json(self.witness_path, witness)
        return witness
