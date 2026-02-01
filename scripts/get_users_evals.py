import requests
import csv
import time

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
        print(f"[ERROR] Error cannot obtain ID for {login} ({res.status_code})")
        return None

def get_user_corrections(user_id):
    corrections = []
    page = 1
    while True:
        url = f"https://api.intra.42.fr/v2/users/{user_id}/scale_teams/as_corrector?page={page}&per_page=100"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            print(f"[ERROR] Failure getting evaluations for {user_id} (page {page})")
            break

        data = res.json()
        if not data:
            break  # No more pages

        corrections.extend(data)
        page += 1
        time.sleep(0.5)  # To avoid the rate limit

    return corrections

def process_correction(correccion):
    comment = correccion.get('comment')
    if comment is None:
        comment = ""
    else:
        comment = comment.replace("\n", " ")

    return {
        "evaluator_login": correccion['corrector']['login'],
        "evaluated": correccion['team']['users'][0]['login'] if correccion['team']['users'] else "N/A",
        "proyect": correccion['team']['project']['name'] if correccion['team'].get('project') else "N/A",
        "final_mark": correccion.get('final_mark', "N/A"),
        "comment": comment,
        "created_at": correccion.get('created_at', "N/A")
    }

def main():
    with open("logins.txt", "r") as f:
        logins = [line.strip() for line in f if line.strip()]

    all_corrections = []

    for login in logins:
        print(f"Processing: {login}")
        user_id = get_user_id(login)
        if user_id is None:
            continue
        time.sleep(3)
        raw_corrections = get_user_corrections(user_id)
        for c in raw_corrections:
            processed = process_correction(c)
            all_corrections.append(processed)

        time.sleep(3)

    keys = ["evaluator_login", "evaluated", "proyect", "final_mark", "comment", "created_at"]
    with open("evaluaciones.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_corrections)

    print(f"Saved {len(all_corrections)} evaluations in evaluations.csv")

if __name__ == "__main__":
    main()
