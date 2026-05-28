# PCK SelfSeed Lineage Propagator v0.3

A standalone, self-contained seed that preserves source lineage and propagates responsibly.

This is not a viral replicator. It is a bounded lineage propagator.

```text
source → seed → child seed → verified lineage → responsible propagation
```

The source can be:
- the artist
- the author
- David Wise
- a human collaborator
- an AI session
- a mixed human/AI artifact
- a file, image, repo, prompt, or document

The seed never treats output as ownerless. It carries lineage.

---

# Core Law

```text
A seed may propagate only if lineage remains intact.
```

---

# AXIOM_0

```text
No state persists without an admissible transition.
```

---

# AXIOM_1

```text
No propagation without source lineage.
```

---

# AXIOM_2

```text
No public child seed may contain private parent data.
```

---

# AXIOM_3

```text
A child may mutate only within delta-bound limits.
```

Default:

```text
delta = 0.00000001
```

---

# AXIOM_4

```text
Bad memory may be transformed into wisdom residue, then pruned.
```

---

# What This Package Does

This package creates a local seed runtime that can:

1. boot a root seed
2. record source attribution
3. verify lineage
4. scan local payloads
5. create a child seed
6. strip private fields before propagation
7. hash parent and child manifests
8. approve, defer, quarantine, or deny propagation
9. write an append-only lineage log

---

# Directory Layout

```text
pck_selfseed_lineage_v03/
  README.md
  manifest.json
  lineage_kernel.py
  demo_lineage_propagator.py
  seed_policy.json
  examples/
    source_manifest.example.json
```

Runtime output:

```text
selfseed_data/
  root_seed.json
  child_seed.json
  lineage_events.jsonl
  witness.json
```

---

# Propagation Gate

A child seed must pass all checks:

```text
source_lineage_present
parent_root_present
private_data_removed
delta_within_limit
child_manifest_hash_valid
rollback_available
policy_allows_publication
```

If any critical check fails:

```text
DENY or QUARANTINE
```

If publication is disabled:

```text
DEFER
```

---

# Source Model

```json
{
  "source_id": "src_hash",
  "source_type": "artist|author|human|ai_session|mixed|file|repo",
  "source_name": "David Wise",
  "source_role": "originator|collaborator|witness|compiler",
  "source_uri": null,
  "source_hash": "sha256...",
  "rights_note": "lineage retained; no ownership erased"
}
```

---

# Seed Model

```json
{
  "seed_id": "seed_hash",
  "parent_seed": null,
  "source": {},
  "root": "sha256...",
  "delta": 0.00000001,
  "visibility": "private|shared|public",
  "payload": {},
  "wisdom": [],
  "policy": {},
  "created": 0
}
```

---

# Responsible Propagation

Responsible propagation means:

```text
fork the seed
preserve source lineage
remove private payloads
retain witness hash
verify child
write lineage event
publish only if policy allows
```

---

# Run Demo

```bash
python demo_lineage_propagator.py
```

Expected:

```text
root seed created
child seed proposed
lineage verified
private payload stripped
propagation decision: DEFER or ALLOW
witness written
```

By default, public propagation is disabled, so the demo returns `DEFER`.
