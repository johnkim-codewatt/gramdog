import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def row_fingerprint(row: Dict[str, Any]) -> str:
    # Stable fingerprint for overlap checks.
    b = json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def split_rows_min_leakage(
    rows: List[Dict[str, Any]], n_valid: int, seed: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if n_valid <= 0:
        raise ValueError("n_valid must be > 0")
    if n_valid >= len(rows):
        raise ValueError(f"n_valid ({n_valid}) must be < total ({len(rows)})")

    rng = random.Random(seed)

    # Group rows by fingerprint so we can prefer singletons (minimizes training-data loss).
    fp_to_indices: Dict[str, List[int]] = {}
    for i, row in enumerate(rows):
        fp = row_fingerprint(row)
        fp_to_indices.setdefault(fp, []).append(i)

    fps = list(fp_to_indices.keys())
    rng.shuffle(fps)
    fps.sort(key=lambda fp: len(fp_to_indices[fp]))  # prefer low-frequency fingerprints

    if len(fps) < n_valid:
        raise RuntimeError(f"not enough unique rows to build valid: unique={len(fps)} need={n_valid}")

    selected_valid_fps = set(fps[:n_valid])

    valid: List[Dict[str, Any]] = []
    for fp in fps[:n_valid]:
        # Choose one representative row per fingerprint.
        idx_list = fp_to_indices[fp]
        valid.append(rows[idx_list[0]])

    # Exclude any training rows that have the same fingerprint as any valid row (prevents leakage).
    train = [row for row in rows if row_fingerprint(row) not in selected_valid_fps]

    return train, valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--train_out", required=True)
    parser.add_argument("--valid_out", required=True)
    parser.add_argument("--n_valid", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--strategy",
        choices=["min_leakage"],
        default="min_leakage",
        help="How to select validation rows from a dataset that may contain duplicates.",
    )
    parser.add_argument(
        "--train_limit",
        type=int,
        default=0,
        help="If > 0, downsample train to this many rows (deterministic by --seed).",
    )
    args = parser.parse_args()

    in_path = Path(args.in_path)
    rows = load_jsonl(in_path)

    # Strategy is currently fixed to min_leakage (keeps train as large as possible while preventing leakage).
    train, valid = split_rows_min_leakage(rows, n_valid=args.n_valid, seed=args.seed)

    if args.train_limit and args.train_limit > 0 and len(train) > args.train_limit:
        rng = random.Random(args.seed)
        idx = list(range(len(train)))
        rng.shuffle(idx)
        train = [train[i] for i in idx[: args.train_limit]]

    write_jsonl(Path(args.train_out), train)
    write_jsonl(Path(args.valid_out), valid)

    print(
        json.dumps(
            {
                "input": str(in_path),
                "total": len(rows),
                "train_out": args.train_out,
                "train_count": len(train),
                "valid_out": args.valid_out,
                "valid_count": len(valid),
                "note": "train excludes any rows whose content matches valid (fingerprint-based).",
                "seed": args.seed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
