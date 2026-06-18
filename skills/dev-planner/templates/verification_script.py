#!/usr/bin/env python3
"""
dev-planner — Verification Script Template
==========================================
Canonical template for Layer 4 verification blocks.
Includes: CLI runner, summary table, and correction-loop harness.

Usage:
    python verification_script.py           # run all
    python verification_script.py V-1.1     # run specific block
    python verification_script.py --list    # list all blocks
"""

import sys
import time
import traceback
from typing import Callable

# ── Configuration ──────────────────────────────────────────────────────────────
MAX_RETRIES = 3          # correction loop retries per block
STOP_ON_FIRST_FAIL = False  # set True for fast-fail mode

# ── Correction Loop Harness ────────────────────────────────────────────────────

def run_with_correction(verify_fn: Callable, block_id: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Run a verification block with a correction loop.
    On failure, surfaces the error for pseudocode patching before retrying.
    Returns True if passed, False if exhausted all retries.
    """
    for attempt in range(1, max_retries + 1):
        try:
            verify_fn()
            return True
        except AssertionError as e:
            print(f"  ✗ [{block_id}] attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                print(f"    → Review pseudocode section marked LOOP-UPDATE for {block_id}")
        except Exception as e:
            print(f"  ✗ [{block_id}] unexpected error (attempt {attempt}/{max_retries})")
            traceback.print_exc()
    return False


# ── Verification Blocks ────────────────────────────────────────────────────────
# Add your project-specific verification functions below.
# Each function must:
#   1. Be named verify_<id> (e.g. verify_1_1 for V-1.1)
#   2. Use assert statements for all checks
#   3. Print "✓ V-X.Y passed" at the end

def verify_1_1():
    """V-1.1 — Template: replace with your first LOW-level check."""
    # setup
    # result = your_function(...)
    
    # assertions
    # assert result is not None, "result must not be None"
    # assert isinstance(result, expected_type), f"expected {expected_type}, got {type(result)}"
    
    print("✓ V-1.1 passed")


def verify_1_2():
    """V-1.2 — Template: replace with your second LOW-level check."""
    # setup
    # data = load_data(...)
    
    # assertions
    # assert len(data) > 0, "data must not be empty"
    # assert data.shape == EXPECTED_SHAPE, f"shape mismatch: {data.shape} != {EXPECTED_SHAPE}"
    
    print("✓ V-1.2 passed")


def verify_2_1():
    """V-2.1 — Template: replace with your first MID-level integration check."""
    # setup
    # result = run_component(...)
    
    # assertions
    # assert result.metric >= THRESHOLD, f"metric={result.metric} < {THRESHOLD}"
    
    print("✓ V-2.1 passed")


# ── Registry ───────────────────────────────────────────────────────────────────
# Map block IDs to their functions. Add new blocks here.

BLOCKS: dict[str, Callable] = {
    "V-1.1": verify_1_1,
    "V-1.2": verify_1_2,
    "V-2.1": verify_2_1,
    # "V-2.2": verify_2_2,
    # "V-3.1": verify_3_1,
}


# ── CLI Runner ─────────────────────────────────────────────────────────────────

def print_summary(results: dict[str, bool]) -> None:
    print("\n" + "═" * 50)
    print("  VERIFICATION SUMMARY")
    print("═" * 50)
    passed = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]
    for block_id, ok in results.items():
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}  {block_id}")
    print("─" * 50)
    print(f"  Passed: {len(passed)} / {len(results)}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
        print("\n  → Patch pseudocode LOOP-UPDATE sections for failed blocks")
    else:
        print("  All blocks passed. ✓")
    print("═" * 50 + "\n")


def main():
    args = sys.argv[1:]

    if "--list" in args:
        print("Available verification blocks:")
        for block_id in BLOCKS:
            fn = BLOCKS[block_id]
            print(f"  {block_id}  —  {fn.__doc__.strip().split(chr(10))[0]}")
        return

    # Filter to specific blocks if requested
    if args:
        targets = {k: BLOCKS[k] for k in args if k in BLOCKS}
        unknown = [k for k in args if k not in BLOCKS]
        if unknown:
            print(f"Unknown block(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(BLOCKS.keys())}")
            sys.exit(1)
    else:
        targets = BLOCKS

    results: dict[str, bool] = {}
    for block_id, verify_fn in targets.items():
        print(f"\n▶ Running {block_id}...")
        t0 = time.perf_counter()
        ok = run_with_correction(verify_fn, block_id)
        elapsed = time.perf_counter() - t0
        results[block_id] = ok
        status = "✓" if ok else "✗"
        print(f"  {status} {block_id} ({elapsed:.2f}s)")
        if not ok and STOP_ON_FIRST_FAIL:
            print(f"\n  Stopping on first failure (STOP_ON_FIRST_FAIL=True)")
            break

    print_summary(results)
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
