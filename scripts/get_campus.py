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
        params.update({"page": page, "per_page": 100})  # 100 items per page
        response = requests.get(endpoint, headers=HEADERS, params=params)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"Error in page {page}: {response.status_code}")
            break

        page_data = response.json()
        if not page_data:
            break  # No more pages
        all_data.extend(page_data)

        print(f"Page {page} with {len(page_data)} elements.")
        page += 1

    return all_data

def save_in_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    all_campus = get_all_paginated(BASE_URL)
    save_in_json("campus_completo.json", all_campus)
    print(f"\nSaved in 'campus_completo.json' with {len(all_campus)} registered.")

if __name__ == "__main__":
    main()
