#!/usr/bin/env python3
"""
show_user_json.py

Uso:
  python show_user_json.py <login> [--raw] [--out FILENAME]

Ejemplos:
  python show_user_json.py josehurt
  python show_user_json.py josehurt --out josehurt.json
"""

import sys
import os
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde el mismo directorio del script
load_dotenv(dotenv_path=Path(__file__).parent / "../.env")

BASE_URL = "https://api.intra.42.fr"
API_BASE = "https://api.intra.42.fr/v2"
UID = os.getenv("UID")
SECRET = os.getenv("SECRET")
TIMEOUT = 15

def get_token(uid, secret):
    if not uid or not secret:
        raise RuntimeError("UID y SECRET no están definidas en el .env")
    res = requests.post(f"{BASE_URL}/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret,
    }, timeout=10)
    res.raise_for_status()
    return res.json().get("access_token")

def fetch_user(login, token):
    url = f"{API_BASE}/users/{login}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers, timeout=TIMEOUT)
    if res.status_code == 404:
        raise FileNotFoundError(f"Usuario '{login}' no encontrado (404)")
    res.raise_for_status()
    return res.json()

def main():
    parser = argparse.ArgumentParser(description="Mostrar JSON completo de un usuario de 42.")
    parser.add_argument("login", help="login del usuario")
    parser.add_argument("--raw", action="store_true", help="Imprime JSON sin formatear (compacto)")
    parser.add_argument("--out", "-o", help="Guardar salida JSON en archivo")
    args = parser.parse_args()

    try:
        token = get_token(UID, SECRET)
    except Exception as e:
        print(f"[ERROR] No se pudo obtener token: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        data = fetch_user(args.login, token)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(3)
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        print(f"[ERROR] HTTP {code}: {e}", file=sys.stderr)
        sys.exit(4)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}", file=sys.stderr)
        sys.exit(5)

    if args.raw:
        out_text = json.dumps(data, ensure_ascii=False)
    else:
        out_text = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text)
        print(f"Guardado en {args.out}")
    else:
        print(out_text)

if __name__ == "__main__":
    main()