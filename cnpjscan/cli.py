"""Linha de comando do cnpj-alfa-scanner."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from .scanner import scan_path
from .classifier import classify
from .report import build_markdown, build_json
from .models import Verdict


def _load_dotenv() -> None:
    """Carrega um .env simples do diretorio atual, sem dependencia externa."""
    import os

    env = Path(".env")
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def _progress(done: int, total: int) -> None:
    pct = int(done / total * 100) if total else 100
    print(f"\r  classificando... {done}/{total} ({pct}%)", end="", file=sys.stderr, flush=True)
    if done >= total:
        print("", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cnpjscan",
        description="Varre um codebase em busca de pontos que quebram com o CNPJ alfanumerico.",
    )
    parser.add_argument("path", help="Arquivo ou diretorio a varrer")
    parser.add_argument("-o", "--out", default="relatorio-cnpj.md", help="Arquivo markdown de saida")
    parser.add_argument("--json", dest="json_out", help="Tambem grava os findings em JSON neste caminho")
    parser.add_argument("--no-llm", action="store_true", help="So' regex, sem chamar a Claude")
    parser.add_argument("--model", help="Modelo da Claude (default: claude-opus-4-8 ou CNPJSCAN_MODEL)")
    parser.add_argument("--version", action="version", version=f"cnpj-alfa-scanner {__version__}")
    args = parser.parse_args(argv)

    _load_dotenv()

    target = Path(args.path)
    if not target.exists():
        print(f"erro: caminho nao encontrado: {args.path}", file=sys.stderr)
        return 2

    print(f"[1/3] varrendo {args.path} ...", file=sys.stderr)
    candidates = scan_path(args.path)
    print(f"      {len(candidates)} candidato(s) suspeito(s).", file=sys.stderr)

    if not candidates:
        print("Nenhum ponto suspeito encontrado. 🎉", file=sys.stderr)
        Path(args.out).write_text(
            build_markdown([], args.path, used_llm=not args.no_llm), encoding="utf-8"
        )
        return 0

    import os

    use_llm = not args.no_llm and bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not args.no_llm and not use_llm:
        print("      aviso: ANTHROPIC_API_KEY nao definido — caindo para modo regex.", file=sys.stderr)

    print(f"[2/3] classificando ({'LLM' if use_llm else 'regex'}) ...", file=sys.stderr)
    findings = classify(candidates, use_llm=use_llm, model=args.model, progress=_progress if use_llm else None)

    print("[3/3] gerando relatorio ...", file=sys.stderr)
    md = build_markdown(findings, args.path, used_llm=use_llm)
    Path(args.out).write_text(md, encoding="utf-8")

    if args.json_out:
        Path(args.json_out).write_text(build_json(findings), encoding="utf-8")

    counts = Counter(f.verdict for f in findings)
    print(
        f"\nPronto: {counts.get(Verdict.BREAKS, 0)} quebra(s), "
        f"{counts.get(Verdict.REVIEW, 0)} p/ revisar, "
        f"{counts.get(Verdict.SAFE, 0)} ok  ->  {args.out}",
        file=sys.stderr,
    )
    # exit code 1 se houver algo que quebra (util em CI)
    return 1 if counts.get(Verdict.BREAKS, 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
