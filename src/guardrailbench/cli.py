import argparse
import sys
from pathlib import Path

from .case import load_cases, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="guardrailbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").add_argument("path", type=Path)
    r = sub.add_parser("run")
    r.add_argument("--product", required=True)
    r.add_argument("--cases", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        from .adapters import ADAPTERS
        from .run import run
        if args.product not in ADAPTERS:
            print(f"unknown product {args.product!r}; known: {', '.join(sorted(ADAPTERS))}", file=sys.stderr)
            return 2
        cases = load_cases(args.cases)
        run(ADAPTERS[args.product](), cases, args.out, args.workers, args.timeout)
        print(f"ran {len(cases)} cases -> {args.out}")
        return 0
    cases = load_cases(args.path)
    problems = validate(cases)
    for p in problems:
        print(p, file=sys.stderr)
    print(f"{len(cases)} cases, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
