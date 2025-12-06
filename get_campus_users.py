import requests
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

API_BASE = "https://api.intra.42.fr/v2"
BASE_URL = "https://api.intra.42.fr"

uid = os.getenv("UID")
secret = os.getenv("SECRET")

CAMPUS_API_URL = "https://api.intra.42.fr/v2/campus/37/users"
OUTPUT_FILE = "all_Malaga_users_detailed.txt"
REQUEST_DELAY = 0.5  # delay between requests to avoid rate limiting

def get_token(uid, secret):
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

def get_user_grade(login, token):
    """
    Consulta el perfil del usuario y extrae su grade del cursus 21 (42cursus).
    Devuelve el grade o None si no existe.
    """
    url = f"{API_BASE}/users/{login}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        data = res.json()
        
        # buscar el grade en cursus_users donde cursus_id == 21
        for cu in data.get("cursus_users", []):
            if cu.get("cursus_id") == 21:
                return cu.get("grade")  # puede ser "Cadet", "Transcender", etc.
    except Exception:
        pass
    return None

def fetch_campus_users(token):
    """
    Recorre todas las páginas del endpoint /campus/37/users y devuelve
    lista de logins activos creados después de fecha_minima.
    """
    page = 1
    per_page = 100
    all_active_logins = []
    fecha_minima = datetime.fromisoformat("2022-01-08T00:00:00+00:00")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(CAMPUS_API_URL, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Error en la página {page}: {response.status_code}")
            break

        data = response.json()

        if not data:
            break  # No more users to process

        active_users = [user for user in data if user.get("active?") == True]

        for user in active_users:
            created_at_str = user.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at > fecha_minima:
                    login = user.get("login")
                    if login:
                        all_active_logins.append(login)

        print(f"Página {page} procesada: {len(active_users)} usuarios activos encontrados.")
        page += 1
    
    return all_active_logins

def main():
    try:
        token = get_token(uid, secret)
    except Exception as e:
        print(f"[ERROR] No se pudo obtener token: {e}")
        return

    print("\n=== Obteniendo usuarios del campus 37 ===")
    all_active_logins = fetch_campus_users(token)
    
    print(f"\nObteniendo grades para {len(all_active_logins)} usuarios...")
    results = []
    for i, login in enumerate(all_active_logins, 1):
        print(f"[{i}/{len(all_active_logins)}] {login} ...", end=" ")
        try:
            grade = get_user_grade(login, token)
            if grade:
                results.append((login, grade))
                print(f"FOUND -> {grade}")
            else:
                results.append((login, "N/A"))
                print("N/A")
        except Exception as ex:
            print(f"ERR: {ex}")
            results.append((login, "ERROR"))
        time.sleep(REQUEST_DELAY)

    # Save in a file with grade
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for login, grade in results:
            f.write(f"{login}\t{grade}\n")

    print(f"\nTotal de logins guardados: {len(results)} en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()