"""Import a day-1 style legacy JSONL into a tenant's SQLite event store.

Usage:
    python scripts/import_legacy.py <file.jsonl> [--tenant will] [--root data]

Prints lines in / events out / appended / skipped. Safe to re-run (deterministic ids).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pios_algo.events import SqliteEventStore  # noqa: E402
from pios_algo.events.upcast import upcast_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--tenant", default="will")
    ap.add_argument("--root", default="data")
    args = ap.parse_args(argv)

    events, report = upcast_file(args.file, args.tenant)
    with SqliteEventStore(args.root, args.tenant) as store:
        result = store.append(events)
        total = store.count()
    print(f"lines_in={report.lines_in} events_out={report.events_out} "
          f"appended={result.appended} skipped={result.skipped_duplicates} store_total={total}")
    print("by_type=" + ", ".join(f"{k}:{v}" for k, v in sorted(report.by_type.items())))
    if report.unmapped_types:
        print("unmapped (stored as DeviationLogged)=" + ", ".join(f"{k}:{v}" for k, v in report.unmapped_types.items()))
    return 0 if report.lines_in == report.events_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
