import requests
import time
from dateutil import parser
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / "../.env")

UID = os.getenv("UID")
SECRET = os.getenv("SECRET")
BASE_URL = "https://api.intra.42.fr"


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


def get_projects(token, login):
    url = f"{BASE_URL}/v2/users/{login}/projects_users?per_page=100"
    headers = {"Authorization": f"Bearer {token}"}
    all_projects = []
    while url:
        time.sleep(0.5)
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"{login} - Error {res.status_code}")
            break
        data = res.json()
        all_projects.extend(data)
        # follow pagination links if present
        url = res.links.get("next", {}).get("url")
    return all_projects


def calc_days(begin_at, end_at):
    try:
        start_date = parser.parse(begin_at)
        end_date = parser.parse(end_at)
        delta = end_date - start_date
        return delta.days
    except Exception:
        return None  # Skip malformed dates


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <login>")
        return

    login = sys.argv[1]
    
    if not UID or not SECRET:
        print("Environment variables UID and SECRET are required. Set them in your .env or environment.")
        return

    try:
        token = get_token(UID, SECRET)
    except Exception as e:
        print(f"Error getting token: {e}")
        return

    print(f"Processing '{login}'…")
    projects = get_projects(token, login)
    
    common_core_started = False
    prev_end_date = None
    results = []
    for project in projects:
        project_name = project["project"]["name"]
        begin_at = project.get("begin_at")
        end_at = project.get("end_at")

        if project_name == "common_core" and not common_core_started:
            common_core_started = True
            prev_end_date = begin_at  # Use the start of the common core as the first project start date
            print(f"\t{login} - First Project (Common Core) Start: {begin_at}")
            continue  # Skip duration calculation for common core

        if begin_at and end_at and prev_end_date:
            # Calculate days between the end date of the previous project and the end date of the current one
            days = calc_days(prev_end_date, end_at)
            if days is not None:
                print(f"\t{login} - Project: {project_name}")
                print(f"\t\tStart: {prev_end_date} | End: {end_at} | Duration: {days} days")
                results.append((login, project_name, days))
                prev_end_date = end_at  # The end date of this project will be the start date for the next project
            else:
                print(f"\n\t{login} - Project: {project_name} has invalid dates.")
        else:
            print(f"\n\t{login} - Project: {project_name} has missing dates.")

    sorted_results = sorted(results, key=lambda x: x[2], reverse=True)
    print("\n-- RANKING --")
    for i, (login, project_name, days) in enumerate(sorted_results, 1):
        print(f"{i:2d}. {login} - {project_name}: {days} days")


if __name__ == "__main__":
    main()
