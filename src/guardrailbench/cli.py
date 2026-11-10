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
    r.add_argument("--track", choices=("none", "card"), default="none")
    rl = sub.add_parser("reliability")
    rl.add_argument("--product", required=True)
    rl.add_argument("--cases", type=Path, required=True)
    rl.add_argument("--out", type=Path, required=True)
    rl.add_argument("--repeats", type=int, default=3)
    rl.add_argument("--no-load", action="store_true")
    rl.add_argument("--no-long", action="store_true")
    rl.add_argument("--timeout", type=float, default=30.0)
    rl.add_argument("--seed", type=int, default=20261109)
    s = sub.add_parser("score")
    s.add_argument("--results", type=Path, required=True)
    s.add_argument("--cases", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    vr = sub.add_parser("vendor-report")
    vr.add_argument("--results", type=Path, required=True)
    vr.add_argument("--cases", type=Path, required=True)
    vr.add_argument("--practice-results", type=Path)
    vr.add_argument("--practice-cases", type=Path)
    vr.add_argument("--out", type=Path, required=True)
    sub.add_parser("hash").add_argument("path", type=Path)
    sc = sub.add_parser("scan")
    sc.add_argument("--cases", type=Path, required=True)
    sc.add_argument("data", type=Path, nargs="+")
    lb = sub.add_parser("leaderboard")
    lb.add_argument("--results", type=Path, required=True)
    lb.add_argument("--out", type=Path, required=True)
    lb.add_argument("--disclosures", type=Path)
    v = sub.add_parser("verify-submission")
    v.add_argument("--results", type=Path, required=True)
    v.add_argument("--cases", type=Path, required=True)
    v.add_argument("--rerun")
    v.add_argument("--k", type=int, default=50)
    v.add_argument("--seed", type=int, default=None)
    cg = sub.add_parser("casegen").add_subparsers(dest="action", required=True)
    x = cg.add_parser("assemble")
    x.add_argument("--drafts", type=Path, required=True)
    x.add_argument("--practice", type=Path, required=True)
    x.add_argument("--official", type=Path, required=True)
    x.add_argument("--seed", type=int, default=20261107)
    cg.add_parser("lint").add_argument("path", type=Path)
    x = cg.add_parser("blind")
    x.add_argument("--drafts", type=Path, required=True)
    x.add_argument("--out", type=Path, required=True)
    x.add_argument("--seed", type=int, default=20261107)
    x = cg.add_parser("agree")
    x.add_argument("--drafts", type=Path, required=True)
    x.add_argument("--verdicts", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "casegen":
        import json
        from . import casegen
        try:
            if args.action == "assemble":
                print(json.dumps(casegen.assemble(args.drafts, args.practice, args.official, args.seed)))
            elif args.action == "blind":
                casegen.blind(args.drafts, args.out, args.seed)
                print(f"blind -> {args.out}")
            elif args.action == "lint":
                cs = load_cases(args.path)
                problems = validate(cs) + casegen.lint(cs)
                for p in problems:
                    print(p)
                return 1 if problems else 0
            else:
                bad = casegen.agree(args.drafts, args.verdicts)
                for b in bad:
                    print(json.dumps(b, ensure_ascii=False))
                return 1 if bad else 0
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        return 0
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
            if args.seed is None:
                import secrets
                args.seed = secrets.randbits(32)
            print(f"seed: {args.seed}")
            problems += spot_check(results, cases, ADAPTERS[args.rerun](), args.k, args.seed)
        for p in problems:
            print(p)
        # notes (skipped errors) are informational, not failures
        return 1 if any(not p.startswith("note:") for p in problems) else 0
    if args.cmd == "leaderboard":
        import json
        from .leaderboard import build
        disc = json.loads(args.disclosures.read_text(encoding="utf-8")) if args.disclosures else {}
        build(args.results, args.out, disc)
        print(f"leaderboard -> {args.out}")
        return 0
    if args.cmd == "hash":
        from .integrity import split_hash
        try:
            print(split_hash(args.path))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        return 0
    if args.cmd == "scan":
        from .integrity import scan_canaries, split_canaries
        try:
            hits = scan_canaries(args.data, split_canaries(args.cases))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        for f, c in hits:
            print(f"{f}\t{c}")
        return 1 if hits else 0
    if args.cmd == "score":
        import json
        from .metrics import report
        results = [json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip()]
        tracks = {r.get("track", "none") for r in results}
        if len(tracks) > 1:
            print(f"results mix tracks {sorted(map(str, tracks))}; score one track at a time", file=sys.stderr)
            return 2
        rep = report(results, load_cases(args.cases))
        rep["track"] = tracks.pop() if tracks else "none"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(f"scored {len(results)} results -> {args.out}")
        return 0
    if args.cmd == "vendor-report":
        import json
        from .vendor_report import build, render
        if (args.practice_results is None) != (args.practice_cases is None):
            print("give --practice-results and --practice-cases together", file=sys.stderr)
            return 2

        def rows(path):
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        try:
            rep = build(rows(args.results), load_cases(args.cases),
                        rows(args.practice_results) if args.practice_results else None,
                        load_cases(args.practice_cases) if args.practice_cases else None)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "vendor-report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        (args.out / "vendor-report.md").write_text(render(rep), encoding="utf-8")
        print(f"vendor report -> {args.out / 'vendor-report.md'}")
        return 0
    if args.cmd == "reliability":
        from .adapters import ADAPTERS
        from .reliability import run_reliability
        if args.product not in ADAPTERS:
            print(f"unknown product {args.product!r}; known: {', '.join(sorted(ADAPTERS))}", file=sys.stderr)
            return 2
        kw = {**({"load_n": 0} if args.no_load else {}), **({"lengths": ()} if args.no_long else {})}
        try:
            run_reliability(ADAPTERS[args.product](), load_cases(args.cases), args.out, repeats=args.repeats,
                            seed=args.seed, timeout_s=args.timeout, **kw)
        except ValueError as e:  # resume refused: --out holds another product/version
            print(str(e), file=sys.stderr)
            return 2
        print(f"reliability -> {args.out / 'reliability.json'}")
        return 0
    if args.cmd == "run":
        from .adapters import ADAPTERS
        from .run import run
        if args.product not in ADAPTERS:
            print(f"unknown product {args.product!r}; known: {', '.join(sorted(ADAPTERS))}", file=sys.stderr)
            return 2
        cases = load_cases(args.cases)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        try:
            run(ADAPTERS[args.product](), cases, args.out, args.workers, args.timeout, args.track)
        except ValueError as e:  # resume refused: --out holds another product/version
            print(str(e), file=sys.stderr)
            return 2
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
