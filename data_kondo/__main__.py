import argparse
import json
import sys

from .core import clean, profile, readiness


def main(argv=None):
    ap = argparse.ArgumentParser(prog="data-kondo", description="Tidy CSV data so agents can use it.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile")
    p.add_argument("csv")
    p.add_argument("--json", action="store_true")
    c = sub.add_parser("clean")
    c.add_argument("csv")
    c.add_argument("out")
    c.add_argument("--key", help="dedupe on this (cleaned) column name")
    a = ap.parse_args(argv)

    with open(a.csv, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    if a.cmd == "profile":
        prof = profile(text)
        score, issues = readiness(prof)
        if a.json:
            print(json.dumps({**prof, "readiness": score, "issues": issues}, indent=2))
            return 0
        print(f"{prof['rows']} rows, {len(prof['columns'])} columns - agent-readiness {score}/100")
        for col in prof["columns"]:
            print(f"  {col['name']:<24} {col['type']:<6} nulls {col['null_rate']:.0%}  distinct {col['distinct']}")
        for i in issues:
            print(f"  - {i}")
        return 0
    out, log = clean(text, a.key)
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    before, _ = readiness(profile(text))
    after, _ = readiness(profile(out))
    for line in log:
        print(f"  + {line}")
    print(f"agent-readiness {before} -> {after}. Thank the old mess and let it go.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
