#!/usr/bin/env python3
"""
nested_kernel.py — PCK recursive nesting runtime

Implements:
- Nested cells
- Parent/child local roots
- Wind / unwind
- Traversal order: upper-right → left → down-left depth-first
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib, json, time, uuid

AXIOM_0 = "No state persists without an admissible transition."
NEST_AXIOM = "No child may update global continuity without parent validation."

PRIMARY_ORDER = ["UR", "L", "DL", "R", "D", "CENTER"]

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()

def now() -> float:
    return time.time()

@dataclass
class NestedEvent:
    source: str
    intent: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: "evt_" + uuid.uuid4().hex)
    timestamp: float = field(default_factory=now)

    def hash(self) -> str:
        return sha256_obj(asdict(self))

@dataclass
class NestedCell:
    cell_id: str
    parent_id: Optional[str]
    position: str = "CENTER"
    state: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    local_root: str = "0" * 64
    status: str = "active"
    created: float = field(default_factory=now)

    def public_view(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "parent_id": self.parent_id,
            "position": self.position,
            "children": self.children,
            "local_root": self.local_root,
            "status": self.status,
            "state": self.state,
        }

class NestedKernel:
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.cells: Dict[str, NestedCell] = {}
        self.global_root = "0" * 64
        self.events: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text())
        self.global_root = data.get("global_root", "0" * 64)
        self.events = data.get("events", [])
        self.cells = {
            cid: NestedCell(**cdata)
            for cid, cdata in data.get("cells", {}).items()
        }

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "global_root": self.global_root,
            "cells": {cid: asdict(cell) for cid, cell in self.cells.items()},
            "events": self.events[-500:],
            "axioms": [AXIOM_0, NEST_AXIOM],
        }
        self.state_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def boot_root(self, cell_id: str = "root") -> NestedCell:
        if cell_id in self.cells:
            return self.cells[cell_id]
        root = NestedCell(cell_id=cell_id, parent_id=None, position="CENTER")
        root.local_root = self.compute_cell_root(root, None)
        self.cells[cell_id] = root
        self.update_global_root()
        self.save()
        return root

    def spawn_child(self, parent_id: str, position: str, cell_id: Optional[str] = None, state: Optional[Dict[str, Any]] = None) -> NestedCell:
        if parent_id not in self.cells:
            raise ValueError(f"parent not found: {parent_id}")
        if position not in PRIMARY_ORDER:
            raise ValueError(f"invalid position: {position}")
        cid = cell_id or f"{parent_id}.{position.lower()}_{uuid.uuid4().hex[:6]}"
        child = NestedCell(
            cell_id=cid,
            parent_id=parent_id,
            position=position,
            state=state or {}
        )
        child.local_root = self.compute_cell_root(child, None)
        self.cells[cid] = child
        self.cells[parent_id].children.append(cid)
        self.recompute_upward(cid)
        self.record("spawn_child", {"parent_id": parent_id, "child_id": cid, "position": position})
        self.save()
        return child

    def apply_event(self, cell_id: str, event: NestedEvent) -> Dict[str, Any]:
        if cell_id not in self.cells:
            raise ValueError(f"cell not found: {cell_id}")
        cell = self.cells[cell_id]

        decision = self.evaluate_event(cell, event)
        old_root = cell.local_root

        if decision["admit"]:
            # Mutate only local state first.
            cell.state.update(event.payload.get("state_delta", {}))
            if event.intent == "quarantine":
                cell.status = "quarantined"
            if event.intent == "heal":
                cell.status = "active"
                cell.state["healed_at"] = event.timestamp

        cell.local_root = self.compute_cell_root(cell, event)
        self.recompute_upward(cell_id)

        rec = {
            "type": "apply_event",
            "cell_id": cell_id,
            "event": asdict(event),
            "decision": decision,
            "old_root": old_root,
            "new_root": cell.local_root,
            "global_root": self.global_root,
        }
        self.events.append(rec)
        self.save()
        return rec

    def evaluate_event(self, cell: NestedCell, event: NestedEvent) -> Dict[str, Any]:
        # Minimal gates.
        if cell.status == "quarantined" and event.intent != "heal":
            return {"admit": False, "reason": "cell_quarantined"}
        if event.intent == "mutate":
            delta = abs(float(event.payload.get("delta", 0)))
            if delta > 0.00000001:
                return {"admit": False, "reason": "delta_exceeds_limit"}
        if event.intent in {"mutate", "preserve", "assimilate", "heal", "quarantine", "learn"}:
            return {"admit": True, "reason": "intent_admissible"}
        return {"admit": False, "reason": "unknown_intent"}

    def compute_cell_root(self, cell: NestedCell, event: Optional[NestedEvent]) -> str:
        material = {
            "cell_id": cell.cell_id,
            "parent_id": cell.parent_id,
            "position": cell.position,
            "state": cell.state,
            "children": [(cid, self.cells[cid].local_root) for cid in cell.children if cid in self.cells],
            "previous_root": cell.local_root,
            "event_hash": event.hash() if event else None,
            "status": cell.status,
        }
        return sha256_obj(material)

    def recompute_upward(self, start_cell_id: str) -> None:
        current = self.cells[start_cell_id]
        current.local_root = self.compute_cell_root(current, None)

        while current.parent_id:
            parent = self.cells[current.parent_id]
            parent.local_root = self.compute_cell_root(parent, None)
            current = parent

        self.update_global_root()

    def update_global_root(self) -> None:
        roots = {cid: cell.local_root for cid, cell in sorted(self.cells.items()) if cell.parent_id is None}
        self.global_root = sha256_obj({
            "axiom": AXIOM_0,
            "nest_axiom": NEST_AXIOM,
            "roots": roots,
        })

    def sort_children_for_traversal(self, children: List[str]) -> List[str]:
        def key(cid: str):
            pos = self.cells[cid].position
            try:
                return PRIMARY_ORDER.index(pos)
            except ValueError:
                return 999
        return sorted(children, key=key)

    def traversal(self, root_id: str = "root") -> List[str]:
        """UR → L → DL depth-first, then remaining children."""
        if root_id not in self.cells:
            return []

        out: List[str] = [root_id]

        def walk(cid: str):
            cell = self.cells[cid]
            ordered = self.sort_children_for_traversal(cell.children)
            for child_id in ordered:
                out.append(child_id)
                # Down-left first again: depth-first recursion prioritizes DL branch.
                walk(child_id)

        walk(root_id)
        return out

    def wind(self, root_id: str = "root") -> Dict[str, Any]:
        """Compress nested child roots upward into global continuity."""
        order = list(reversed(self.traversal(root_id)))
        for cid in order:
            self.cells[cid].local_root = self.compute_cell_root(self.cells[cid], None)
        self.update_global_root()
        rec = {"type": "wind", "root_id": root_id, "order": order, "global_root": self.global_root}
        self.events.append(rec)
        self.save()
        return rec

    def unwind(self, root_id: str = "root") -> Dict[str, Any]:
        """Emit readable nested continuity in deterministic traversal order."""
        order = self.traversal(root_id)
        trail = [self.cells[cid].public_view() for cid in order]
        rec = {"type": "unwind", "root_id": root_id, "order": order, "trail": trail, "global_root": self.global_root}
        self.events.append({"type": "unwind", "root_id": root_id, "order": order, "global_root": self.global_root})
        self.save()
        return rec

    def record(self, typ: str, payload: Dict[str, Any]) -> None:
        self.events.append({"type": typ, "payload": payload, "timestamp": now(), "global_root": self.global_root})
