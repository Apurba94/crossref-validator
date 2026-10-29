"""Command-line interface for crossref-validator."""
import argparse
import json
import time

from .core import crossref_fetch, parse_bibtex, validate


def main(argv=None, fetch=None):
    ap = argparse.ArgumentParser(prog="crossref-validator", description="Check BibTeX entries against Crossref.")
    ap.add_argument("bibfile")
    ap.add_argument("--mailto", help="your e-mail, sent to Crossref for its polite pool")
    ap.add_argument("--threshold", type=float, default=0.9, help="title similarity threshold")
    ap.add_argument("--delay", type=float, default=0.1)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if fetch is None:
        def fetch(doi):
            time.sleep(args.delay)
            return crossref_fetch(doi, args.mailto)
    with open(args.bibfile, encoding="utf-8") as fh:
        results = validate(parse_bibtex(fh.read()), fetch, args.threshold)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if r["status"] == "ok":
                continue
            print("%-25s %s" % (r["key"], r["status"]))
            for field, local, remote, sev in r["issues"]:
                print("    %-7s %-8s local=%r crossref=%r" % (sev, field, local[:60], remote[:60]))
        counts = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(", ".join("%s: %d" % kv for kv in sorted(counts.items())))
    return 1 if any(r["status"] in ("mismatch", "doi-not-found") for r in results) else 0
