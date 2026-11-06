"""dirlint core: config loading, rule metadata, and the read-only scanner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "0.1.0"

RULE_META = {
    "R0": {"title": "Top-level whitelist", "severity": "high",
           "desc": "Only configured entries may live at the workspace root."},
    "R1": {"title": "Same-name nesting", "severity": "medium",
           "desc": "A directory repeating its parent's name: a move went wrong."},
    "R2": {"title": "Stray files at project roots", "severity": "medium",
           "desc": "Logs, backups, temp files, images, or archives at a project root."},
    "R3": {"title": "Backup / timestamp dirs", "severity": "medium",
           "desc": "Backup folders and bare timestamp folders outside the archive."},
    "R4": {"title": "Temp dirs in projects", "severity": "medium",
           "desc": "temp/tmp/downloads/_scratch inside a project or tool root."},
    "R5": {"title": "Workspace structure", "severity": "low",
           "desc": "Unregistered directories inside the workspace zone."},
    "R6": {"title": "Retired directories", "severity": "low",
           "desc": "Directories declared retired but still occupying space."},
    "R7": {"title": "Duplicate files", "severity": "low",
           "desc": "Byte-identical copies under project/tool zones."},
}

DEFAULT_IGNORE_DIRS = ["node_modules", ".git", ".venv", "venv", "__pycache__",
                       ".pnpm-store", ".codegraph", ".impeccable"]
DEFAULT_ROOT_FILES = ["README.md", "readme.md", "LICENSE", "LICENSE.txt", "COPYING",
                      "CHANGELOG.md", ".gitignore", ".gitattributes", ".npmrc",
                      ".env.example", ".editorconfig", "package.json",
                      "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
                      "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
                      "Pipfile", "docker-compose.yml", "docker-compose.yaml",
                      "Dockerfile", "Makefile", "vite.config.js", "vite.config.ts",
                      "tsconfig.json", "index.html", "AGENTS.md", "CLAUDE.md",
                      "pagefile.sys", "swapfile.sys", "hiberfil.sys"]
SUSPICIOUS_EXT = {".log", ".bak", ".tmp", ".err", ".diff", ".orig", ".dmp", ".swp"}
SUSPICIOUS_IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
SUSPICIOUS_ARCHIVE = {".zip", ".7z", ".rar", ".tar", ".gz"}
BACKUP_RE = re.compile(r"(^|[._-])(bak|backup|old|copy|副本|备份)([._-]|$)", re.I)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(-\d{2}(-\d{2})?)?$")
TEMP_DIR_NAMES = {"temp", "tmp", "downloads", "_scratch", "scratch"}

DEFAULTS = {
    "allowedTop": [],
    "ignoredTop": ["$RECYCLE.BIN", "System Volume Information"],
    "allowedFilesAtRoot": DEFAULT_ROOT_FILES,
    "zones": {"projects": [], "tools": [], "workspace": [], "archive": [], "cache": []},
    "workspaceAllowed": ["temp", "temp-workspace", "cleanup", ".automation-lock"],
    "retired": [],
    "scan": {"maxDepth": 4, "ignoreDirs": DEFAULT_IGNORE_DIRS},
    "rules": {"topLevel": True, "nesting": True, "projectRootFiles": True,
              "backups": True, "tempDirs": True, "workspace": True,
              "retired": True, "duplicates": False},
    "duplicates": {"minBytes": 1048576},
}


@dataclass
class Finding:
    rule: str
    severity: str
    path: str
    rel: str
    reason: str
    fix: str
    size: int = 0
    reason_key: str = ""
    fix_key: str = ""


@dataclass
class ScanResult:
    root: str
    generated_at: str
    duration_ms: int
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rule_meta: dict = field(default_factory=lambda: RULE_META)
    seen: set = field(default_factory=set)

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.findings)

    def to_dict(self) -> dict:
        by_rule: dict[str, int] = {}
        for f in self.findings:
            by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
        return {
            "root": self.root,
            "generatedAt": self.generated_at,
            "durationMs": self.duration_ms,
            "summary": {"count": len(self.findings), "bytes": self.total_bytes,
                        "byRule": by_rule},
            "findings": [f.__dict__ for f in self.findings],
            "warnings": self.warnings,
            "ruleMeta": self.rule_meta,
        }


def deep_merge(base, over):
    out = dict(base)
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None) -> dict:
    if not path:
        return deep_merge(DEFAULTS, {})
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return deep_merge(DEFAULTS, data)


def human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def dir_size(path: Path, ignore_dirs: set[str], budget: int = 200_000) -> int:
    total = 0
    seen = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            try:
                total += (Path(current) / name).stat().st_size
            except OSError:
                pass
            seen += 1
            if seen >= budget:
                return total
    return total


class Scanner:
    def __init__(self, root: Path, cfg: dict):
        self.root = root.resolve()
        self.cfg = cfg
        self.rules = cfg["rules"]
        self.ignore = set(cfg["scan"]["ignoreDirs"])
        self.max_depth = int(cfg["scan"]["maxDepth"])
        self.result = ScanResult(root=str(self.root), generated_at="", duration_ms=0)

    # -- helpers ---------------------------------------------------------
    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def zone_roots(self, name: str) -> list[Path]:
        roots = []
        for rel in self.cfg["zones"].get(name, []):
            path = (self.root / rel).resolve()
            if path.is_dir():
                roots.append(path)
        return roots

    def add(self, rule: str, path: Path, reason: str, fix: str, size: int | None = None,
            reason_key: str = "", fix_key: str = ""):
        key = (rule, str(path).lower())
        if key in self.result.seen:
            return
        self.result.seen.add(key)
        meta = RULE_META[rule]
        if size is None:
            size = dir_size(path, self.ignore) if path.is_dir() else (
                path.stat().st_size if path.exists() else 0)
        self.result.findings.append(Finding(
            rule=rule, severity=meta["severity"], path=str(path), rel=self.rel(path),
            reason=reason, fix=fix, size=size, reason_key=reason_key, fix_key=fix_key))

    def walk_dirs(self, base: Path):
        """Yield directories under base up to maxDepth, pruning ignored names."""
        for current, dirs, _ in os.walk(base):
            path = Path(current)
            depth = len(path.relative_to(base).parts)
            if depth >= self.max_depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if d not in self.ignore]
            for name in list(dirs):
                yield path / name

    # -- rules -----------------------------------------------------------
    def rule_top_level(self):
        allowed_dirs = {a.lower() for a in self.cfg["allowedTop"]}
        ignored = {a.lower() for a in self.cfg["ignoredTop"]}
        allowed_files = {a.lower() for a in self.cfg["allowedFilesAtRoot"]}
        try:
            entries = list(self.root.iterdir())
        except OSError as exc:
            self.result.warnings.append(f"cannot read root: {exc}")
            return
        for entry in entries:
            name = entry.name.lower()
            if name in ignored:
                continue
            if entry.is_dir():
                if name not in allowed_dirs:
                    self.add("R0", entry, "Directory is not on the top-level whitelist.",
                             "Move it into a configured zone, or delete it if it has no value.",
                             reason_key="top.dir", fix_key="fix.top")
            elif name not in allowed_files:
                self.add("R0", entry, "File is not on the top-level whitelist.",
                         "Move it into a subdirectory or the process workspace.",
                         reason_key="top.file", fix_key="fix.top")

    def rule_nesting(self):
        # Only zone roots are checked: `tools/tools` is an accident, while a
        # Python package named after its project (`dirlint/dirlint`) is normal.
        for zone in ("projects", "tools"):
            for base in self.zone_roots(zone):
                try:
                    children = list(base.iterdir())
                except OSError:
                    continue
                for child in children:
                    if child.is_dir() and child.name.lower() == base.name.lower():
                        self.add("R1", child, "Zone root contains a directory of its own name.",
                                 "Flatten it into the zone root.",
                                 reason_key="nest", fix_key="fix.nest")

    def rule_project_root_files(self):
        allowed = {a.lower() for a in self.cfg["allowedFilesAtRoot"]}
        roots = self.zone_roots("projects")
        for zone_root in roots:
            for project in zone_root.iterdir():
                if not project.is_dir() or project.name in self.ignore:
                    continue
                try:
                    files = [f for f in project.iterdir() if f.is_file()]
                except OSError:
                    continue
                for file in files:
                    name = file.name.lower()
                    if name in allowed:
                        continue
                    ext = file.suffix.lower()
                    if (ext in SUSPICIOUS_EXT or ext in SUSPICIOUS_IMG
                            or ext in SUSPICIOUS_ARCHIVE or BACKUP_RE.search(name)):
                        self.add("R2", file, "Stray file at the project root.",
                                 "Delete logs and backups; move real assets into docs/ "
                                 "or a runtime-data directory.",
                                 reason_key="rootfile", fix_key="fix.rootfile")

    def rule_backups(self):
        # Only project zones: installed programs keep their own backup/copy
        # folders, and the process workspace is provisional by definition.
        for base in self.zone_roots("projects"):
            for child in self.walk_dirs(base):
                parts = set(child.parts)
                if "archive" in parts or "runtime-data" in parts:
                    continue
                if child.parent.name == "data" and child.name == "backup":
                    continue
                if BACKUP_RE.search(child.name) or TIMESTAMP_RE.match(child.name):
                    self.add("R3", child, "Backup or bare timestamp directory.",
                             "Keep only a unique copy, archive it, and delete the rest.",
                             reason_key="backup", fix_key="fix.backup")

    def rule_temp_dirs(self):
        roots = self.zone_roots("projects")
        for zone_root in roots:
            for project in zone_root.iterdir():
                if not project.is_dir() or project.name in self.ignore:
                    continue
                for child in project.iterdir():
                    if child.is_dir() and child.name.lower() in TEMP_DIR_NAMES:
                        self.add("R4", child, "Temporary directory inside a project zone.",
                                 "Move it to the process workspace and delete the folder.",
                                 reason_key="tempdir", fix_key="fix.tempdir")

    def rule_workspace(self):
        allowed = {a.lower() for a in self.cfg["workspaceAllowed"]}
        for base in self.zone_roots("workspace"):
            for child in base.iterdir():
                if not child.is_dir() or child.name in self.ignore:
                    continue
                if child.name.lower() in allowed:
                    continue
                reason = ("Bare timestamp directory." if TIMESTAMP_RE.match(child.name)
                          else "Directory is not registered in the workspace.")
                key = "ws.timestamp" if TIMESTAMP_RE.match(child.name) else "ws.unregistered"
                self.add("R5", child, reason,
                         "Archive or delete it; task folders belong in the task workspace.",
                         reason_key=key, fix_key="fix.ws")

    def rule_retired(self):
        for name in self.cfg["retired"]:
            path = self.root / name
            if path.exists():
                self.add("R6", path, "Directory was declared retired.",
                         "Archive it if it is the only copy, then delete it.",
                         reason_key="retired", fix_key="fix.retired")

    def rule_duplicates(self):
        opts = self.cfg["duplicates"]
        min_bytes = int(opts["minBytes"])
        roots = self.zone_roots("projects") + self.zone_roots("tools")
        by_size: dict[int, list[Path]] = {}
        for base in roots:
            for current, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in self.ignore]
                for name in files:
                    path = Path(current) / name
                    try:
                        size = path.stat().st_size
                    except OSError:
                        continue
                    if size >= min_bytes:
                        by_size.setdefault(size, []).append(path)
        for size, paths in by_size.items():
            if len(paths) < 2:
                continue
            by_hash: dict[str, list[Path]] = {}
            for path in paths:
                digest = self._hash(path)
                if digest:
                    by_hash.setdefault(digest, []).append(path)
            for group in by_hash.values():
                if len(group) < 2:
                    continue
                group.sort(key=lambda p: len(p.as_posix()))
                keep, extras = group[0], group[1:]
                self.add("R7", keep, f"Byte-identical copies: {len(group)} files, "
                                     f"keep {self.rel(keep)}.",
                         "Delete the other copies: " + ", ".join(self.rel(p) for p in extras),
                         size=size * len(extras), reason_key="dupe", fix_key="fix.dupe")

    @staticmethod
    def _hash(path: Path) -> str | None:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError:
            return None
        return digest.hexdigest()

    # -- run -------------------------------------------------------------
    def run(self) -> ScanResult:
        started = time.perf_counter()
        if self.rules.get("topLevel"):
            self.rule_top_level()
        if self.rules.get("nesting"):
            self.rule_nesting()
        if self.rules.get("projectRootFiles"):
            self.rule_project_root_files()
        if self.rules.get("backups"):
            self.rule_backups()
        if self.rules.get("tempDirs"):
            self.rule_temp_dirs()
        if self.rules.get("workspace"):
            self.rule_workspace()
        if self.rules.get("retired"):
            self.rule_retired()
        if self.rules.get("duplicates"):
            self.rule_duplicates()
        self.result.findings.sort(key=lambda f: (f.rule, -f.size, f.rel))
        from datetime import datetime, timezone
        self.result.generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.result.duration_ms = int((time.perf_counter() - started) * 1000)
        return self.result


def scan(root: str | Path, cfg: dict) -> ScanResult:
    return Scanner(Path(root), cfg).run()
