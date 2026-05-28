#!/usr/bin/env python3
from pathlib import Path
from typing import Any, Dict, List
import argparse, hashlib, json, time, fnmatch

IGNORE_DIRS = {".git", ".pck", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
IGNORE_PATTERNS = {"*.pyc", "*.tmp", "*.log", ".DS_Store", "Thumbs.db"}

AXIOMS = [
    "No state persists without an admissible transition.",
    "No self-state is current unless lineage can be replayed.",
    "No orphan rejoins the whole without local evidence."
]

def now() -> float:
    return time.time()

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str), encoding="utf-8")

def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, default=str) + "\n")

def should_ignore(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except Exception:
        return True
    if set(rel.parts) & IGNORE_DIRS:
        return True
    return any(fnmatch.fnmatch(path.name, pat) for pat in IGNORE_PATTERNS)

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def scan_files(root: Path) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or should_ignore(p, root):
            continue
        try:
            st = p.stat()
            files.append({
                "path": str(p.relative_to(root)).replace("\\", "/"),
                "sha256": file_hash(p),
                "size": st.st_size,
                "mtime": st.st_mtime
            })
        except Exception as e:
            files.append({"path": str(p), "error": str(e)})
    out = {"root_path": str(root.resolve()), "file_count": len(files), "files": files}
    out["manifest_hash"] = sha256_obj(files)
    return out

class ContinuityShell:
    def __init__(self, folder: Path):
        self.root = folder.resolve()
        self.pck = self.root / ".pck"
        self.state_path = self.pck / "state.json"
        self.lineage_path = self.pck / "lineage.jsonl"
        self.manifest_path = self.pck / "manifest.json"
        self.orphans_path = self.pck / "orphans.json"
        self.healed_path = self.pck / "healed.json"

    def load_state(self) -> Dict[str, Any]:
        return read_json(self.state_path, {
            "root": "0" * 64,
            "transitions": 0,
            "created": now(),
            "axioms": AXIOMS
        })

    def scan(self) -> Dict[str, Any]:
        prev_state = self.load_state()
        prev_manifest = read_json(self.manifest_path, {"files": [], "manifest_hash": None})
        manifest = scan_files(self.root)

        prev_by_path = {f.get("path"): f for f in prev_manifest.get("files", []) if f.get("path")}
        cur_by_path = {f.get("path"): f for f in manifest.get("files", []) if f.get("path")}

        missing = sorted(set(prev_by_path) - set(cur_by_path))
        new = sorted(set(cur_by_path) - set(prev_by_path))
        changed = sorted(p for p in set(prev_by_path) & set(cur_by_path)
                         if prev_by_path[p].get("sha256") != cur_by_path[p].get("sha256"))

        old_orphans = read_json(self.orphans_path, {"orphans": []})
        old_orphan_paths = {o.get("path") for o in old_orphans.get("orphans", [])}
        healed = sorted(set(cur_by_path) & old_orphan_paths)

        transition = {
            "type": "scan",
            "timestamp": now(),
            "previous_root": prev_state["root"],
            "previous_manifest_hash": prev_manifest.get("manifest_hash"),
            "manifest_hash": manifest["manifest_hash"],
            "file_count": manifest["file_count"],
            "new": new,
            "changed": changed,
            "missing": missing,
            "healed": healed
        }
        transition["transition_hash"] = sha256_obj(transition)
        new_root = sha256_obj({
            "previous_root": prev_state["root"],
            "transition_hash": transition["transition_hash"],
            "manifest_hash": manifest["manifest_hash"],
            "axioms": AXIOMS
        })

        state = {
            "root": new_root,
            "previous_root": prev_state["root"],
            "transitions": int(prev_state.get("transitions", 0)) + 1,
            "updated": now(),
            "manifest_hash": manifest["manifest_hash"],
            "file_count": manifest["file_count"],
            "axioms": AXIOMS,
            "last_transition_hash": transition["transition_hash"]
        }

        orphan_records = [
            {
                "path": p,
                "last_seen_hash": prev_by_path[p].get("sha256"),
                "last_seen_size": prev_by_path[p].get("size"),
                "orphaned_at": now()
            } for p in missing
        ]

        write_json(self.manifest_path, manifest)
        write_json(self.state_path, state)
        write_json(self.orphans_path, {"orphans": orphan_records})
        write_json(self.healed_path, {"healed": healed, "updated": now()})
        append_jsonl(self.lineage_path, {**transition, "new_root": new_root})

        return {"state": state, "transition": transition}

    def status(self) -> Dict[str, Any]:
        state = self.load_state()
        orphans = read_json(self.orphans_path, {"orphans": []})
        healed = read_json(self.healed_path, {"healed": []})
        return {
            "root_path": str(self.root),
            "continuity_root": state.get("root"),
            "transitions": state.get("transitions", 0),
            "file_count": state.get("file_count", 0),
            "orphans": len(orphans.get("orphans", [])),
            "healed": len(healed.get("healed", [])),
            "updated": state.get("updated")
        }

    def verify(self) -> Dict[str, Any]:
        state = self.load_state()
        manifest = scan_files(self.root)
        ok = state.get("manifest_hash") == manifest.get("manifest_hash")
        return {
            "ok": ok,
            "stored_manifest_hash": state.get("manifest_hash"),
            "current_manifest_hash": manifest.get("manifest_hash"),
            "message": "continuity current" if ok else "drift detected; run scan"
        }

    def export(self) -> Dict[str, Any]:
        export_obj = {
            "state": self.load_state(),
            "manifest": read_json(self.manifest_path, {}),
            "orphans": read_json(self.orphans_path, {}),
            "healed": read_json(self.healed_path, {}),
            "exported": now()
        }
        export_obj["export_hash"] = sha256_obj(export_obj)
        out = self.root / "pck_continuity_export.json"
        write_json(out, export_obj)
        return {"export_path": str(out), "export_hash": export_obj["export_hash"]}

def main() -> int:
    ap = argparse.ArgumentParser(description="PCK Continuity Shell")
    ap.add_argument("command", choices=["scan", "status", "verify", "export"])
    ap.add_argument("folder", nargs="?", default=".")
    args = ap.parse_args()
    shell = ContinuityShell(Path(args.folder))
    result = getattr(shell, args.command)()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
