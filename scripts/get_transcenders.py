#!/usr/bin/env python3
import os
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / "../.env")

API_BASE = "https://api.intra.42.fr/v2"
BASE_URL = "https://api.intra.42.fr"
UID = os.getenv("UID")
SECRET = os.getenv("SECRET")

INPUT_FILES = ["users/all_campus_users.txt"]
OUTPUT_FILE = "users_transcender_and_alumni.txt"

REQUEST_DELAY = 0.5  # delay between requests to avoid rate limiting

def get_token(uid, secret):
    if not uid or not secret:
        raise RuntimeError("UID y SECRET should be on .env")
    res = requests.post(f"{BASE_URL}/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret
    }, timeout=10)
    res.raise_for_status()
    return res.json()["access_token"]

def read_logins():
    for fname in INPUT_FILES:
        p = Path(fname)
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return [l.strip() for l in f if l.strip()]
    return []

# Receives the parsed JSON of the user and returns (is_transcender, is_alumni).
def detect_transcender_and_alumni(data):
    is_transcender = False
    is_alumni = False

    # alumni detection (top-level)
    if data.get("alumni?") is True:
        is_alumni = True
    if data.get("alumnized_at"):
        is_alumni = True

    # traverse cursus_users
    for cu in data.get("cursus_users", []):
        # prefer cursus_id == 21 (42cursus) but accept slug match too
        try:
            grade = cu.get("grade")
            cursus = cu.get("cursus") or {}
            cursus_id = cu.get("cursus_id") or cursus.get("id")
            cursus_slug = (cursus.get("slug") or "").lower()
            if grade and isinstance(grade, str) and "transcender" in grade.lower():
                # if it's a transcender grade on any cursus, flag it
                is_transcender = True
            elif cursus_id == 21 or "42cursus" in cursus_slug:
                # check grade for this main cursus
                if grade and isinstance(grade, str) and "transcender" in grade.lower():
                    is_transcender = True
        except Exception:
            continue

    return bool(is_transcender), bool(is_alumni)

def user_check(login, token):
    url = f"{API_BASE}/users/{login}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 404:
        return False, False
    res.raise_for_status()
    data = res.json()
    return detect_transcender_and_alumni(data)

def main():
    logins = read_logins()
    if not logins:
        print("No files present or no logins found (busqué: {})".format(", ".join(INPUT_FILES)))
        return
    try:
        token = get_token(UID, SECRET)
    except Exception as e:
        print(f"[ERROR] cannot get TOKEN: {e}")
        return

    results = []
    total = len(logins)
    for i, login in enumerate(logins, 1):
        print(f"[{i}/{total}] {login} ...", end=" ")
        try:
            is_transcender, is_alumni = user_check(login, token)
            if is_transcender or is_alumni:
                labels = []
                if is_transcender:
                    labels.append("Transcender")
                if is_alumni:
                    labels.append("Alumni")
                results.append((login, ",".join(labels)))
                print("FOUND :", ",".join(labels))
            else:
                print("no")
        except requests.HTTPError as he:
            code = he.response.status_code if he.response is not None else "?"
            print(f"HTTP {code}")
        except Exception as ex:
            print(f"ERR: {ex}")
        time.sleep(REQUEST_DELAY)

    if results:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for login, labels in results:
                f.write(f"{login}\t{labels}\n")
    print(f"\Done. {len(results)} Outer Core users registered in {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()