# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: Python 3.11+ standard library only (`http.server`) for the scanner and the local UI server; one hand-written HTML/CSS/JS page with no build step. Chosen so the tool installs with `pip install -e .` and runs offline on any machine that already has Python.

## Users

Developers, solo maintainers, and small teams who keep many projects, tools, and datastores under one workspace root. Their job: finish a task without leaving scratch scripts, logs, backups, and duplicated copies behind, and prove it to themselves or a reviewer.

## Product Purpose

`dirlint` audits a workspace against placement rules the team defines: which top-level entries are allowed, where project artifacts live, where process files belong, and which directories are retired. It reports violations with a size estimate and a concrete fix. Success is a second scan that passes.

## Positioning

Rules are a small config file, not a language or framework convention. The scanner is read-only, stdlib-only, offline, and runs against any directory tree, so it works on a drive used by several agents and tools, not only inside one repository.

## Operating Context

- A long-lived workspace drive where multiple agents and tools write files.
- After a task: cleanup and handoff; before a release: leak and layout check.
- A weekly scheduled run that writes a report and compares against the previous one.
- The web UI is opened on demand, locally, beside the terminal.

## Capabilities and Constraints

- Rules: top-level whitelist, same-name nesting, stray files at project roots, backup/timestamp directories, temp directories inside project zones, workspace structure, retired directories, optional duplicate-file detection.
- Output: terminal table, JSON, and a local web UI. Report only: the scanner never deletes or moves anything.
- Config: one JSON file (`dirlint.json`); zones are relative paths, defaults are deliberately empty so nothing is assumed about an unknown workspace.
- Constraints: Python standard library only; no network calls; binds the UI to 127.0.0.1.
- Undecided: packaging to PyPI; authentication (none needed for a localhost tool).

## Brand Commitments

Name: `dirlint`. License: MIT. Voice: plain, precise, no exclamation marks. Report, never mutate.

## Evidence on Hand

Real scan output from a multi-project workspace (see `docs/screenshots/`). No customer logos, testimonials, or benchmarks exist and none may be invented.

## Product Principles

1. Report, never mutate. Every finding carries the fix as text; the user decides.
2. Convention lives in config. The tool assumes nothing about a directory it has not been configured for.
3. Make the correct path the default: scaffolds, cache locations, and sample configs point at the right place before the first mistake.
4. One command to value: no daemon, no build step, no dependency tree.
5. Evidence over claims: every rule states what it checks and why.

## Accessibility & Inclusion

WCAG AA contrast for text and controls; full keyboard operation; `prefers-reduced-motion` respected; no information conveyed by color alone (rule codes and labels accompany every severity color).
