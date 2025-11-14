import requests
from datetime import datetime
import os

API_BASE = "https://api.intra.42.fr/v2"
TOKEN_URL = f"{API_BASE}/oauth/token"

uid = os.getenv("UID")
secret = os.getenv("SECRET")

API_URL = "https://api.intra.42.fr/v2/campus/37/users"


def get_token():
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret
    })
    resp.raise_for_status()
    return resp.json()["access_token"]



headers = {
    "Authorization": f"Bearer {get_token()}"
}

page = 1
per_page = 100  # máx allowed by the API
all_active_logins = []

# Minimum date (ISO 8601 format)
fecha_minima = datetime.fromisoformat("2025-08-08T00:00:00+00:00")
while True:
    params = {
        "page": page,
        "per_page": per_page
    }

    response = requests.get(API_URL, headers=headers, params=params)

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

# Save in a file
with open("piscina_actual.txt", "w") as f:
    for login in all_active_logins:
        f.write(f"{login}\n")

print(f"\nTotal de logins activos guardados: {len(all_active_logins)}")
