#!/usr/bin/env python3
"""Gera um pacote ZIP com tudo o que o cliente precisa para instalar o BPO."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "dist" / "bpo_instalacao.zip"

FILES_TO_INCLUDE: Tuple[Tuple[str, str], ...] = (
    ("README.md", "README.md"),
    ("requirements.txt", "requirements.txt"),
    ("installers/01_windows_installer.ps1", "installers/01_windows_installer.ps1"),
    ("installers/02_linux_installer.sh", "installers/02_linux_installer.sh"),
    ("installers/README.md", "installers/README.md"),
    ("docs/manual_canva.md", "docs/manual_canva.md"),
    ("docs/pacote_instalacao.md", "docs/pacote_instalacao.md"),
)

DIRECTORIES_TO_INCLUDE: Tuple[Tuple[str, str], ...] = (
    ("bpo_app/frontend", "frontend"),
)


def _resolve_item(source: str, target: str) -> Dict[str, str]:
    src_path = ROOT / source
    if not src_path.exists():
        raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {source}")
    return {"source": str(src_path), "target": target}


def _iter_directory_items(source: str, target_root: str) -> Iterable[Dict[str, str]]:
    base = ROOT / source
    if not base.exists():
        raise FileNotFoundError(f"Diretório obrigatório não encontrado: {source}")
    for path in base.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(base).as_posix()
        yield {"source": str(path), "target": f"{target_root}/{relative}"}


def build_bundle(output: Path, include_frontend: bool = True) -> Dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_items = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for source, target in FILES_TO_INCLUDE:
            info = _resolve_item(source, target)
            bundle.write(info["source"], info["target"])
            manifest_items.append({"type": "file", **info})

        if include_frontend:
            for source, target_root in DIRECTORIES_TO_INCLUDE:
                for info in _iter_directory_items(source, target_root):
                    bundle.write(info["source"], info["target"])
                    manifest_items.append({"type": "asset", **info})

        manifest = {
            "count": len(manifest_items),
            "items": manifest_items,
        }
        bundle.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    return {"archive": str(output), "count": len(manifest_items)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Gera um pacote ZIP com scripts de instalação, manual e frontend "
            "para compartilhamento rápido com clientes."
        )
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Caminho do arquivo ZIP de saída (padrão: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Não incluir os arquivos da interface web no pacote.",
    )
    args = parser.parse_args()

    result = build_bundle(args.output, include_frontend=not args.skip_frontend)
    print(
        "Pacote gerado em {path} contendo {count} itens.".format(
            path=result["archive"],
            count=result["count"],
        )
    )


if __name__ == "__main__":
    main()
