import requests
import time
from dateutil import parser
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

UID = os.getenv("UID")
SECRET = os.getenv("SECRET")
BASE_URL = "https://api.intra.42.fr"


def leer_logins(filename="users/users.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def get_token(uid, secret):
    # mostrar solo un mask del secret para depuración
    print("get_token -> UID:", uid)
    print("get_token -> SECRET mask:", (secret[:4] + "..." + secret[-4:]) if secret else None)

    res = requests.post(f"{BASE_URL}/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret,
    }, timeout=10)

    if res.status_code != 200:
        print("get_token status:", res.status_code)
        try:
            print("get_token response json:", res.json())
        except Exception:
            print("get_token raw response:", repr(res.text))
    res.raise_for_status()
    return res.json()["access_token"]


def get_locations(token, login):
    url = f"{BASE_URL}/v2/users/{login}/locations?per_page=100"
    headers = {"Authorization": f"Bearer {token}"}
    all_locations = []
    while url:
        time.sleep(0.5)
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"{login} - Error {res.status_code}")
            break
        data = res.json()
        all_locations.extend(data)
        # follow pagination links if present
        url = res.links.get("next", {}).get("url")
    return all_locations


def calcular_horas(locations):
    total_seconds = 0
    for loc in locations:
        if loc.get("end_at") and loc.get("begin_at"):
            try:
                inicio = parser.parse(loc["begin_at"])
                fin = parser.parse(loc["end_at"])
                total_seconds += (fin - inicio).total_seconds()
            except Exception:
                # skip malformed dates
                continue
    return round(total_seconds / 3600, 2)


def main():
    # Print only, do not write files
    logins = leer_logins()
    if not logins:
        print("El archivo 'users/users.txt' está vacío o no existe.")
        return

    if not UID or not SECRET:
        print("Environment variables UID and SECRET are required. Set them in your .env or environment.")
        return
    print("UID :", UID)
    print("SECRET :", SECRET)

    try:
        token = get_token(UID, SECRET)
    except Exception as e:
        print(f"Error obteniendo token: {e}")
        return

    resultados = []
    for login in logins:
        print(f"Procesando '{login}'…")
        locations = get_locations(token, login)
        horas = calcular_horas(locations)
        resultados.append((login, horas))
        print(f"  → {login}: {horas:.2f} horas")

    # Mostrar ranking ordenado de mayor a menor en la terminal
    resultados_ordenados = sorted(resultados, key=lambda x: x[1], reverse=True)
    print("\n=== RANKING (mayor a menor) ===")
    for i, (login, horas) in enumerate(resultados_ordenados, 1):
        print(f"{i:2d}. {login}: {horas:.2f} horas")


if __name__ == "__main__":
    main()
