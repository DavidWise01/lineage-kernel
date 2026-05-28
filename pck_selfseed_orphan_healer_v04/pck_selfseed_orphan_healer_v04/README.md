# PCK SelfSeed Orphan Healer v0.4

Adds stitching + healing for orphaned seeds that were once part of the whole.

This extends the lineage propagator:

```text
source → seed → child seed → orphan → scan → verify → heal → reattach
```

---

# Core Law

```text
No orphan rejoins the whole without lineage proof and safety validation.
```

---

# Orphan Definition

An orphan seed is a seed that has one or more of:

```text
parent_seed missing
parent_root missing
witness missing
broken lineage pointer
private/public boundary unknown
valid source but detached root
```

An orphan is not automatically bad.

It is:

```text
a detached continuity fragment requiring reconciliation
```

---

# Healing Outcomes

```text
REATTACH     valid lineage; safely rejoined
QUARANTINE   suspicious or unsafe; held for review
ASSIMILATE   raw seed pruned, wisdom residue retained
REJECT       invalid or hostile; no continuity claim admitted
DEFER        insufficient evidence; wait for more context
```

---

# Stitch Protocol

```text
1. scan orphan directory
2. parse candidate seed
3. verify source lineage
4. verify parent/witness evidence
5. strip private fields
6. compare root hash
7. compute relationship score
8. decide reattach/quarantine/assimilate/reject/defer
9. update healed graph
10. write witness
```

---

# Relationship Score

A seed can prove relation through:

```text
source_id match
parent_seed match
parent_root match
shared witness hash
payload lineage marker
wisdom/residue reference
compatible delta
compatible policy version
```

---

# Run Demo

```bash
python demo_orphan_healer.py
```

Creates:
```text
orphan_healer_data/
  whole/
  orphans/
  healed_graph.json
  stitch_events.jsonl
  witness.json
```

---

# Design Rule

The healer does not blindly merge.

It acts like an immune system:

```text
recognize self
repair damaged self
quarantine uncertain self
reject non-self
extract wisdom from failed self
```
