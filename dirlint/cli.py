"""Command line entry points for dirlint."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from .core import VERSION, human_bytes, load_config, scan

BAD_CHARS = re.compile(r'[\\/:*?"<>|\s]+')
TASK_TEMPLATE = """# Task: {name}

| Field | Value |
|---|---|
| Created | {date} |
| Project | {project} |
| Home | process workspace: temporary scripts, logs, diffs, intermediate captures |

## Expected output (fill in before starting)

- Project artifacts: (to be moved into the project and referenced by docs)
- Process files: (stay here, delete when done)
- Conclusions: (to be written to the knowledge base)

## Close-out

- [ ] Project artifacts moved to their final zone
- [ ] Duplicates removed; one canonical copy remains
- [ ] Conclusions written down
- [ ] This directory deleted or its retention justified
"""


def cmd_scan(args) -> int:
    cfg = load_config(args.config)
    if args.duplicates:
        cfg["rules"]["duplicates"] = True
    result = scan(args.root, cfg)
    payload = result.to_dict()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if result.findings else 0

    summary = payload["summary"]
    print(f"dirlint {VERSION}  root={Path(args.root).resolve()}")
    print(f"{summary['count']} findings · {human_bytes(summary['bytes'])} · "
          f"{result.duration_ms} ms")
    if not result.findings:
        print("PASS")
        return 0
    for finding in result.findings:
        print(f"  {finding.rule}  {human_bytes(finding.size):>9}  {finding.rel}")
        print(f"       {finding.reason}")
        print(f"       fix: {finding.fix}")
    if result.warnings:
        print(f"{len(result.warnings)} warnings")
        for warning in result.warnings[:5]:
            print(f"  ! {warning}")
    return 1


def cmd_new_task(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    slug = BAD_CHARS.sub("-", args.name.strip()).strip("-")
    if not slug:
        print("error: task name is empty", file=sys.stderr)
        return 2
    target = workspace / f"{dt.date.today():%Y%m%d}-{slug}"
    if target.exists():
        print(target)
        return 0
    target.mkdir(parents=True, exist_ok=True)
    (target / "README.md").write_text(
        TASK_TEMPLATE.format(name=args.name.strip(), date=dt.date.today(),
                             project=args.project or "—"),
        encoding="utf-8")
    print(target)
    return 0


def cmd_serve(args) -> int:
    from .server import serve

    serve(root=args.root, config=args.config, port=args.port,
          open_browser=not args.no_browser)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dirlint",
        description="Read-only placement audit for a workspace directory tree.")
    parser.add_argument("--version", action="version", version=f"dirlint {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="scan a root and report violations")
    scan_p.add_argument("--root", default=".", help="directory to audit")
    scan_p.add_argument("--config", help="path to dirlint.json")
    scan_p.add_argument("--json", action="store_true", help="machine-readable output")
    scan_p.add_argument("--duplicates", action="store_true",
                        help="also hash files to find byte-identical copies")
    scan_p.set_defaults(func=cmd_scan)

    task_p = sub.add_parser("new-task", help="create a compliant task directory")
    task_p.add_argument("name", help="task name")
    task_p.add_argument("--workspace", required=True,
                        help="process workspace directory, e.g. workspace/temp-workspace")
    task_p.add_argument("--project", help="related project name")
    task_p.set_defaults(func=cmd_new_task)

    serve_p = sub.add_parser("serve", help="start the local web UI")
    serve_p.add_argument("--root", default=".", help="directory to audit")
    serve_p.add_argument("--config", help="path to dirlint.json")
    serve_p.add_argument("--port", type=int, default=8765)
    serve_p.add_argument("--no-browser", action="store_true")
    serve_p.set_defaults(func=cmd_serve)
    return parser


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
