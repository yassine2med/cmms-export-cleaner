"""Command line entry: python -m cmmsclean messy.csv -o clean.csv"""
from __future__ import annotations

import argparse
import sys

from .cleaner import OUTPUT_COLUMNS, clean_rows, format_report, map_headers, read_records, write_rows


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="cmmsclean", description="Normalize a messy CMMS CSV export")
    parser.add_argument("csv", help="input export")
    parser.add_argument("-o", "--output", default="clean.csv", help="clean output file")
    parser.add_argument("--rejects", default="rejects.csv", help="file for rows that cannot be used")
    args = parser.parse_args(argv)
    try:
        headers, records = read_records(args.csv)
        result = clean_rows(records, map_headers(headers))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_rows(args.output, result.rows, OUTPUT_COLUMNS)
    print(format_report(result))
    print(f"wrote {args.output}")
    if result.rejects:
        write_rows(args.rejects, result.rejects, OUTPUT_COLUMNS + ["reason"])
        print(f"wrote {args.rejects}")
    return 0
