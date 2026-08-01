"""Spec 93 -- generate the synthetic Quote-to-Order benchmark dataset.

Usage:
    python scripts/generate_quote_to_order_dataset.py [--seed 92] [--out docs/benchmark/datasets]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from erpguard.benchmark.dataset import write_dataset
from erpguard.benchmark.dataset_generator import generate_cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=92)
    parser.add_argument("--out", type=Path, default=Path("docs/benchmark/datasets"))
    parser.add_argument("--version", type=str, default=None, help="Defaults to 'quote_to_order_v1_seed{seed}'")
    args = parser.parse_args()

    dataset_version = args.version or f"quote_to_order_v1_seed{args.seed}"
    cases = generate_cases(seed=args.seed)
    manifest = write_dataset(args.out, dataset_version, cases)

    print(f"Generated {manifest['case_count']} cases -> {dataset_version}")
    print(f"Category counts: {manifest['category_counts']}")
    print(f"Dataset hash: {manifest['dataset_hash']}")
    print(f"Written to: {args.out / (dataset_version + '.jsonl')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
