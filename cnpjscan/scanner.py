"""Passo 1 — descoberta deterministica. Varre arquivos e coleta candidatos.

Nao altera nada e nao chama LLM. So' regex + I/O.
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import Candidate
from .patterns import rules_for

# Extensoes de codigo que vale a pena varrer.
SCAN_EXTENSIONS = {
    ".php",
    ".py",
    ".rb",
    ".java",
    ".cs",
    ".go",
    ".rs",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".vue",
    ".sql",
    ".sqlx",
    ".html",
    ".blade.php",
}

# Diretorios que nunca interessam.
SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".next",
    ".nuxt",
    "coverage",
    "storage",
    ".idea",
    ".vscode",
}

CONTEXT_RADIUS = 3
MAX_FILE_BYTES = 2_000_000  # ignora arquivos gigantes (minificados etc.)


def _ext_of(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return ".blade.php"
    return path.suffix.lower()


def _build_context(lines: list[str], idx: int) -> str:
    start = max(0, idx - CONTEXT_RADIUS)
    end = min(len(lines), idx + CONTEXT_RADIUS + 1)
    out = []
    for i in range(start, end):
        marker = ">>" if i == idx else "  "
        out.append(f"{marker} {i + 1:5}| {lines[i].rstrip()}")
    return "\n".join(out)


def scan_file(path: Path) -> list[Candidate]:
    ext = _ext_of(path)
    rules = rules_for(ext)
    if not rules:
        return []
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return []

    lines = text.splitlines()
    found: list[Candidate] = []
    seen: set[tuple[str, int, str]] = set()

    for idx, line in enumerate(lines):
        context = None
        line_lower = line.lower()
        for rule in rules:
            m = rule.pattern.search(line)
            if not m:
                continue
            if rule.requires_cnpj:
                if context is None:
                    context = _build_context(lines, idx)
                if "cnpj" not in line_lower and "cnpj" not in context.lower():
                    continue
            if context is None:
                context = _build_context(lines, idx)
            key = (str(path), idx + 1, rule.id)
            if key in seen:
                continue
            seen.add(key)
            found.append(
                Candidate(
                    file=str(path),
                    line=idx + 1,
                    rule_id=rule.id,
                    rule_desc=rule.desc,
                    severity=rule.severity,
                    language=ext,
                    matched_text=line.strip()[:300],
                    context=context,
                )
            )
    return found


def scan_path(root: str) -> list[Candidate]:
    root_path = Path(root)
    if root_path.is_file():
        return scan_file(root_path)

    results: list[Candidate] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in sorted(filenames):
            p = Path(dirpath) / fname
            if _ext_of(p) in SCAN_EXTENSIONS:
                results.extend(scan_file(p))
    return results
