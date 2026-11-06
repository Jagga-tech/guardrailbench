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
    s = sub.add_parser("score")
    s.add_argument("--results", type=Path, required=True)
    s.add_argument("--cases", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    sub.add_parser("hash").add_argument("path", type=Path)
    sc = sub.add_parser("scan")
    sc.add_argument("--cases", type=Path, required=True)
    sc.add_argument("data", type=Path, nargs="+")
    v = sub.add_parser("verify-submission")
    v.add_argument("--results", type=Path, required=True)
    v.add_argument("--cases", type=Path, required=True)
    v.add_argument("--rerun")
    v.add_argument("--k", type=int, default=50)
    v.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    if args.cmd == "verify-submission":
        from .adapters import ADAPTERS
        from .submission import check_complete, load_results, spot_check
        if args.rerun and args.rerun not in ADAPTERS:
            print(f"unknown product {args.rerun!r}; known: {', '.join(sorted(ADAPTERS))}", file=sys.stderr)
            return 2
        cases = load_cases(args.cases)
        results, problems = load_results(args.results)
        problems += check_complete(results, cases)
        if args.rerun:
            problems += spot_check(results, cases, ADAPTERS[args.rerun](), args.k, args.seed)
        for p in problems:
            print(p)
        # notes (skipped errors) are informational, not failures
        return 1 if any(not p.startswith("note:") for p in problems) else 0
    if args.cmd == "hash":
        from .integrity import split_hash
        print(split_hash(args.path))
        return 0
    if args.cmd == "scan":
        from .integrity import scan_canaries
        hits = scan_canaries(args.data, {c.canary for c in load_cases(args.cases)})
        for f, c in hits:
            print(f"{f}\t{c}")
        return 1 if hits else 0
    if args.cmd == "score":
        import json
        from .metrics import report
        results = [json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip()]
        args.out.write_text(json.dumps(report(results, load_cases(args.cases)), indent=2), encoding="utf-8")
        print(f"scored {len(results)} results -> {args.out}")
        return 0
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
