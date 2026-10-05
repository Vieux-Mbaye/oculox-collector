#!/usr/bin/env python3

"""Install the shared Arkime viewer secret and validate collector reachback."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
VALID_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:-]*$")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def update_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    replacement = f"{key}={value}"
    result: list[str] = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            result.append(replacement)
            found = True
        else:
            result.append(line)
    if not found:
        result.append(replacement)
    path.write_text("\n".join(result) + "\n", encoding="utf-8")
    path.chmod(0o600)


def configure(bundle: Path, project_dir: Path = PROJECT_DIR) -> tuple[bool, str]:
    bundle_secret_path = bundle.resolve() / "arkime-viewer.env"
    bundle_secret = read_env(bundle_secret_path).get("ARKIME_PASSWORD_SECRET", "")
    if not bundle_secret or any(char in bundle_secret for char in "\r\n"):
        raise SystemExit(f"Secret Arkime absent ou invalide : {bundle_secret_path}")

    live = read_env(project_dir / "config" / "arkime-live.env")
    live_enabled = live.get("ARKIME_LIVE_CAPTURE", "false").lower() == "true"
    node_host = live.get("ARKIME_LIVE_NODE_HOST", "").strip()
    if live_enabled and (not node_host or not VALID_HOST.fullmatch(node_host)):
        raise SystemExit(
            "Arkime Live est activé mais ARKIME_LIVE_NODE_HOST est vide ou invalide. "
            "Dans l’assistant, renseignez l’IP ou le DNS du Collecteur joignable depuis le Core."
        )

    arkime_secret_path = project_dir / "config" / "arkime-secret.env"
    update_env(arkime_secret_path, "ARKIME_PASSWORD_SECRET", bundle_secret)

    return live_enabled, node_host


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()

    live_enabled, node_host = configure(args.bundle)
    print("Secret Arkime partagé importé depuis le bundle Core.")
    secret_length = len(read_env(args.bundle.resolve() / "arkime-viewer.env")["ARKIME_PASSWORD_SECRET"])
    if secret_length < 16:
        print(
            "AVERTISSEMENT : le secret Arkime du Core fait moins de 16 caractères ; "
            "planifiez une rotation coordonnée après la recette."
        )
    if live_enabled:
        print(f"Retour Arkime configuré vers le Collecteur : {node_host}:8005")
    else:
        print("Arkime Live est désactivé ; aucun retour PCAP sur 8005 n’est requis.")


if __name__ == "__main__":
    os.umask(0o077)
    main()
