# PCK Nested Kernel v0.2
## Wind / Unwind Runtime for `(1) : (1)`

This version adds actual recursive containment to the Personal Continuity Kernel.

The model:

```text
(1) : (1)
```

Meaning:

```text
left  (1) = nested interior continuity
right (1) = mirrored exterior continuity
:         = active stitch / kernel valve / traversal seam
```

The system can now:

```text
wind   = descend into nested cells and compress into local roots
unwind = ascend out of nested cells and expose continuity back to parent/root
```

---

# Traversal Order

The traversal reads like this:

```text
start upper-right
go left
then down-left first
then down-left first again
repeat recursively
```

This is implemented as a deterministic geometric traversal order:

```text
UR → L → DL → DL.child → DL.child...
```

In code this becomes:

```text
upper_right
left
down_left depth-first
other children after primary path
```

This gives the nesting a stable read/unread order.

---

# Core Runtime Objects

## NestedCell

Each cell has:

```json
{
  "cell_id": "cell",
  "parent_id": "parent_or_null",
  "local_root": "hash",
  "state": {},
  "children": [],
  "position": "UR|L|DL|R|D|CENTER",
  "status": "active|quarantined|merged|pruned"
}
```

## NestedKernel

The kernel can:

```text
spawn_child(parent, position)
apply_event(cell, event)
wind(root)
unwind(root)
validate_child_transition(child, parent)
update_local_root(cell)
update_global_root()
```

---

# Wind

Wind means:

```text
outer continuity → inner nested compression
```

Operationally:

```text
visit cells in traversal order
evaluate each local state
compress child roots into parent root
update global root
```

---

# Unwind

Unwind means:

```text
inner nested continuity → exterior readable sequence
```

Operationally:

```text
visit cells in traversal order
emit lineage trail
emit state summaries
emit root chain
```

---

# Invariant

```text
No child may update global continuity without parent validation.
```

Child cells may explore locally. Parent/root decides whether the result enters shared continuity.

---

# Minimal Execution

```bash
python demo_nested_boot.py
```

Expected output:

```text
spawn root
spawn upper-right
spawn left
spawn down-left
spawn down-left child
wind
unwind
print traversal
print root chain
```

---

# Final Compression

```text
Cell explores.
Child roots compress.
Parent validates.
Kernel stitches.
Root witnesses.
Nest winds.
Nest unwinds.
```
