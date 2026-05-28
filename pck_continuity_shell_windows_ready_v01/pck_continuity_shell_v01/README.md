# PCK Continuity Shell v0.1

A local continuity shell for fractured project data.

It scans a folder, hashes files, records lineage, detects drift, and creates a `.pck/` continuity root.

## Commands

```bash
python pck_continuity_shell.py scan .
python pck_continuity_shell.py status .
python pck_continuity_shell.py verify .
python pck_continuity_shell.py export .
```

## Windows EXE build

Run:

```bat
build_windows_exe.bat
```

That creates:

```text
dist\PCKContinuityShell.exe
```

Then:

```bat
dist\PCKContinuityShell.exe scan C:\path\to\project
```

## What it writes

```text
.pck/
  state.json
  lineage.jsonl
  manifest.json
  orphans.json
  healed.json
```

## Core law

```text
previous_root + file_manifest + transition = new_root
```
