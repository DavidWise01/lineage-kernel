#!/usr/bin/env python3
from pathlib import Path
from pck_kernel import PCKernel, Event

DATA = Path("./pck_data")

def main():
    kernel = PCKernel(
        state_path=DATA / "state.json",
        log_path=DATA / "events.jsonl"
    )

    print("Booting PCK Bare Metal Seed")
    print("Current root:", kernel.state.root)

    first = kernel.apply(Event(
        source="system",
        intent="spawn",
        visibility="private",
        payload={
            "cell_id": "cell_genesis",
            "delta": 0.00000001,
            "purpose": "self-persistent seed exploration"
        }
    ))

    print("Decision:", first["decision"])
    print("Reason:", first["reason"])
    print("New root:", first["new_root"])

    mutate = kernel.apply(Event(
        source="cell_genesis",
        intent="mutate",
        visibility="private",
        payload={"delta": 0.00000001, "candidate": "adjacent_state_probe"}
    ))

    print("Mutation:", mutate["decision"], mutate["reason"])

if __name__ == "__main__":
    main()
