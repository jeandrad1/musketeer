import requests
import csv
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / "../.env")

API_BASE = "https://api.intra.42.fr/v2"
BASE_URL = "https://api.intra.42.fr"
UID = os.getenv("UID")
SECRET = os.getenv("SECRET")

# Token
def get_token(uid, secret):
    # show just one mask of the secret for debugging
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

ACCESS_TOKEN = get_token(UID, SECRET)

USERNAME = "mfuente-"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}


def get_user_id(login):
    print(f"Obtaining user id of '{login}'…")
    res = requests.get(f"{API_BASE}/users/{login}", headers=HEADERS)
    res.raise_for_status()
    return res.json()["id"]


def get_all_evaluations(user_id):
    print("Downloading all completed evaluations…")
    evaluations = []
    page = 1

    while True:
        res = requests.get(
            f"{API_BASE}/scale_teams",
            headers=HEADERS,
            params={
                "filter[filled]": "true",
                "sort": "-created_at",
                "page[number]": page,
                "page[size]": 100
            }
        )
        res.raise_for_status()
        data = res.json()
        if not data:
            break
        evaluations.extend(data)
        page += 1

    return evaluations


def filter_received(evaluations, user_id):
    print("Filtering received evaluations…")
    return [e for e in evaluations if e.get("user", {}).get("id") == user_id]


def save_to_csv(evaluations, filename="../results/received_evaluations.csv"):
    print(f"Saved in '{filename}'…")
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Evaluator", "Proyect", "Result"])

        for e in evaluations:
            date = e.get("created_at", "")[:10]
            corrector = e.get("evaluator", {}).get("login", "")
            project = e.get("team", {}).get("project_gitlab_path", "")
            passed = e.get("final_mark", None)
            result = "Success" if passed and passed > 0 else "Failure"
            writer.writerow([date, corrector, project, result])

    print(f"Saved {len(evaluations)} evaluations.")


def main():
    try:
        user_id = get_user_id(USERNAME)
        all_evals = get_all_evaluations(user_id)
        received = filter_received(all_evals, user_id)
        save_to_csv(received)
    except requests.HTTPError as e:
        print(f"HTTP Error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
