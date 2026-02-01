import requests
import csv
import time

# TOKEN DE ACCESO
ACCESS_TOKEN = ""

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def get_user_id(login):
    url = f"https://api.intra.42.fr/v2/users/{login}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json()['id']
    else:
        print(f"[ERROR] No se pudo obtener el ID de {login} ({res.status_code})")
        return None

def get_user_corrections(user_id):
    corrections = []
    page = 1
    while True:
        url = f"https://api.intra.42.fr/v2/users/{user_id}/scale_teams/as_corrector?page={page}&per_page=100"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            print(f"[ERROR] Fallo obteniendo evaluaciones de {user_id} (página {page})")
            break

        data = res.json()
        if not data:
            break  # No more pages

        corrections.extend(data)
        page += 1
        time.sleep(0.5)  # To avoid the rate limit

    return corrections

def procesar_correccion(correccion):
    comentario = correccion.get('comment')
    if comentario is None:
        comentario = ""
    else:
        comentario = comentario.replace("\n", " ")

    return {
        "login_corrector": correccion['corrector']['login'],
        "evaluado": correccion['team']['users'][0]['login'] if correccion['team']['users'] else "N/A",
        "proyecto": correccion['team']['project']['name'] if correccion['team'].get('project') else "N/A",
        "final_mark": correccion.get('final_mark', "N/A"),
        "comentario": comentario,
        "created_at": correccion.get('created_at', "N/A")
    }

def main():
    with open("logins_activos.txt", "r") as f:
        logins = [line.strip() for line in f if line.strip()]

    all_corrections = []

    for login in logins:
        print(f"Procesando: {login}")
        user_id = get_user_id(login)
        if user_id is None:
            continue
        time.sleep(3)
        raw_corrections = get_user_corrections(user_id)
        for c in raw_corrections:
            processed = procesar_correccion(c)
            all_corrections.append(processed)

        time.sleep(3)

    keys = ["login_corrector", "evaluado", "proyecto", "final_mark", "comentario", "created_at"]
    with open("evaluaciones.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_corrections)

    print(f"✅ Se guardaron {len(all_corrections)} evaluaciones en evaluaciones.csv")

if __name__ == "__main__":
    main()
