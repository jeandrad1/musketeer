import requests
import json

BASE_URL = "https://api.intra.42.fr/v2/campus"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def get_all_paginated(endpoint, params=None):
    if params is None:
        params = {}

    all_data = []
    page = 1
    while True:
        params.update({"page": page, "per_page": 100})  # Hasta 100 por página
        response = requests.get(endpoint, headers=HEADERS, params=params)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"❌ Error en la página {page}: {response.status_code}")
            break

        page_data = response.json()
        if not page_data:
            break  # No hay más páginas
        all_data.extend(page_data)

        print(f"✅ Página {page} descargada con {len(page_data)} elementos.")
        page += 1

    return all_data

def guardar_en_json(nombre_archivo, datos):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

def main():
    todos_los_campus = get_all_paginated(BASE_URL)
    guardar_en_json("campus_completo.json", todos_los_campus)
    print(f"\n📁 Guardado en 'campus_completo.json' con {len(todos_los_campus)} registros.")

if __name__ == "__main__":
    main()
