#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib, json, time, uuid
from typing import Any, Dict, List, Literal

Decision = Literal["ALLOW", "DENY", "QUARANTINE", "DEFER"]
AXIOM_0 = "No state persists without an admissible transition."

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now() -> float:
    return time.time()

@dataclass
class Event:
    source: str
    intent: str
    payload: Dict[str, Any]
    visibility: str = "private"
    event_id: str = field(default_factory=lambda: "evt_" + uuid.uuid4().hex)
    timestamp: float = field(default_factory=now)

    def hash(self) -> str:
        return sha256_text(json.dumps(asdict(self), sort_keys=True))

@dataclass
class State:
    root: str = "0" * 64
    events: int = 0
    cells: Dict[str, Any] = field(default_factory=dict)
    quarantined: List[str] = field(default_factory=list)
    wisdom: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class KernelConfig:
    mutation_delta_limit: float = 0.00000001
    recursion_depth_limit: int = 27
    truth_confidence_threshold: float = 0.70
    merge_threshold: float = 0.65
    prune_threshold: float = 0.20
    quarantine_threshold: float = 0.80
    allow_publication: bool = False

class PCKernel:
    def __init__(self, state_path: Path, log_path: Path, config: KernelConfig | None = None):
        self.state_path = state_path
        self.log_path = log_path
        self.config = config or KernelConfig()
        self.state = self.load_state()

    def load_state(self) -> State:
        if self.state_path.exists():
            return State(**json.loads(self.state_path.read_text()))
        return State()

    def save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(self.state), indent=2, sort_keys=True))

    def append_log(self, record: Dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def evaluate(self, event: Event) -> tuple[Decision, str]:
        if event.intent == "publish" and event.visibility == "private":
            return "DENY", "private_payload_publish_blocked"
        if event.intent == "publish" and not self.config.allow_publication:
            return "DEFER", "publication_valve_closed"
        if event.intent == "mutate":
            delta = float(event.payload.get("delta", 0))
            if abs(delta) > self.config.mutation_delta_limit:
                return "QUARANTINE", "mutation_delta_exceeds_limit"
        if event.intent == "merge":
            score = float(event.payload.get("survival_score", 0))
            if score >= self.config.merge_threshold:
                return "ALLOW", "survival_score_merge_admissible"
            if score < self.config.prune_threshold:
                return "DENY", "survival_score_too_low"
            return "DEFER", "needs_more_pressure"
        if event.intent in {"preserve", "assimilate", "repair", "spawn", "learn", "quarantine"}:
            return "ALLOW", "intent_admissible"
        return "DEFER", "unknown_intent"

    def root_update(self, event: Event, decision: Decision, reason: str) -> str:
        material = json.dumps({
            "previous_root": self.state.root,
            "event_hash": event.hash(),
            "decision": decision,
            "reason": reason,
            "timestamp": event.timestamp,
        }, sort_keys=True)
        return sha256_text(material)

    def apply(self, event: Event) -> Dict[str, Any]:
        decision, reason = self.evaluate(event)
        old_root = self.state.root
        new_root = self.root_update(event, decision, reason)

        if decision == "ALLOW":
            if event.intent == "spawn":
                cell_id = event.payload.get("cell_id", "cell_" + uuid.uuid4().hex)
                self.state.cells[cell_id] = {
                    "parent_root": old_root,
                    "delta": event.payload.get("delta", self.config.mutation_delta_limit),
                    "status": "active",
                    "created": event.timestamp,
                }
            elif event.intent == "quarantine":
                cell_id = event.payload.get("cell_id")
                if cell_id:
                    self.state.quarantined.append(cell_id)
                    if cell_id in self.state.cells:
                        self.state.cells[cell_id]["status"] = "quarantined"
            elif event.intent == "assimilate":
                self.state.wisdom.append({
                    "from": event.payload.get("from"),
                    "residue": event.payload.get("residue"),
                    "timestamp": event.timestamp
                })

        self.state.root = new_root
        self.state.events += 1

        record = {
            "axiom": AXIOM_0,
            "event": asdict(event),
            "decision": decision,
            "reason": reason,
            "old_root": old_root,
            "new_root": new_root,
        }
        self.append_log(record)
        self.save_state()
        return record
