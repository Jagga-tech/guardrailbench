import argparse
import sys
from pathlib import Path

from .case import load_cases, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="guardrailbench")
    ap.add_subparsers(dest="cmd", required=True).add_parser("validate").add_argument("path", type=Path)
    args = ap.parse_args(argv)
    cases = load_cases(args.path)
    problems = validate(cases)
    for p in problems:
        print(p, file=sys.stderr)
    print(f"{len(cases)} cases, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
