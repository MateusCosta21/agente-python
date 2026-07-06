"""Linha de comando do cnpj-alfa-scanner."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from .classifier import classify
from .llm import api_key_present, resolve_provider
from .models import Verdict
from .report import build_json, build_markdown
from .scanner import scan_path


def _load_dotenv() -> None:
    """Carrega um .env simples do diretorio atual, sem dependencia externa."""
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
    parser.add_argument(
        "-o", "--out", default="relatorio-cnpj.md", help="Arquivo markdown de saida"
    )
    parser.add_argument(
        "--json", dest="json_out", help="Tambem grava os findings em JSON neste caminho"
    )
    parser.add_argument("--no-llm", action="store_true", help="So' regex, sem chamar a Claude")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="v2: gera correcoes para as QUEBRAS e um .patch (dry-run)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="v2: aplica as correcoes no working tree (implica --fix)",
    )
    parser.add_argument(
        "--fix-out", default="cnpj-fixes.patch", help="Arquivo .patch de saida (v2)"
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "deepseek"],
        help="Provider de LLM (default: anthropic ou CNPJSCAN_PROVIDER)",
    )
    parser.add_argument(
        "--model",
        help="Modelo do provider (default: claude-opus-4-8 / deepseek-chat ou CNPJSCAN_MODEL)",
    )
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

    provider = resolve_provider(args.provider)
    use_llm = not args.no_llm and api_key_present(provider)
    if not args.no_llm and not use_llm:
        print(
            f"      aviso: chave do provider '{provider}' nao definida — caindo para modo regex.",
            file=sys.stderr,
        )

    rotulo = f"LLM/{provider}" if use_llm else "regex"
    print(f"[2/3] classificando ({rotulo}) ...", file=sys.stderr)
    findings = classify(
        candidates,
        use_llm=use_llm,
        model=args.model,
        provider=provider,
        progress=_progress if use_llm else None,
    )

    want_fix = args.fix or args.apply
    fixes = None
    patch = None
    if want_fix:
        if not use_llm:
            print(
                "erro: --fix/--apply exigem um provider de LLM (defina a chave, sem --no-llm).",
                file=sys.stderr,
            )
            return 2
        from .fixer import apply_fix_to_text, generate_fixes, unified_patch

        print("[3/4] gerando correcoes (v2) ...", file=sys.stderr)
        try:
            fixes = generate_fixes(
                findings, model=args.model, provider=provider, progress=_progress
            )
        except RuntimeError as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 2
        patch = unified_patch(fixes)
        real_fixes = [fx for fx in fixes if fx.original != fx.fixed]
        if patch.strip():
            Path(args.fix_out).write_text(patch, encoding="utf-8")
            print(f"      {len(real_fixes)} correcao(oes) -> {args.fix_out}", file=sys.stderr)
        else:
            print("      nenhuma correcao gerada.", file=sys.stderr)

        if args.apply and real_fixes:
            by_file: dict[str, list] = {}
            for fx in real_fixes:
                by_file.setdefault(fx.file, []).append(fx)
            for file, ff in by_file.items():
                src = Path(file).read_text(encoding="utf-8", errors="ignore")
                Path(file).write_text(apply_fix_to_text(src, ff), encoding="utf-8")
            print(
                f"      aplicadas em {len(by_file)} arquivo(s). Revise com `git diff`.",
                file=sys.stderr,
            )

    step = "[4/4]" if want_fix else "[3/3]"
    print(f"{step} gerando relatorio ...", file=sys.stderr)
    md = build_markdown(
        findings, args.path, used_llm=use_llm, fixes=fixes, patch=patch, applied=args.apply
    )
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
