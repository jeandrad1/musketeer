import requests
from collections import defaultdict, Counter
from openpyxl import Workbook
import os
import time
import json
from collections import defaultdict, Counter

API_BASE = "https://api.intra.42.fr/v2"
TOKEN_URL = f"{API_BASE}/oauth/token"

uid = os.getenv("UID")
secret = os.getenv("SECRET")

# CONFIGURATION
ORIGIN_FILE = "users/users.txt"
DESTINY_FILE = "results/results.xlsx"

# Colors
class Color:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

# Data Storage Structures.
evaluations_map = defaultdict(Counter)  # evaluator-> {evaluated -> times}
user_levels = {}  # login -> level

# Safe request with delays
def safe_request(method, url, headers=None, params=None, data=None, retries=5, delay=3):
    for attempt in range(retries):
        try:
            if method.lower() == 'get':
                return requests.get(url, headers=headers, params=params, timeout=10)
            elif method.lower() == 'post':
                return requests.post(url, headers=headers, data=data, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"{Color.YELLOW}   REattampt {attempt + 1}/{retries} because of connection error: {e}{Color.RESET}")
            time.sleep(delay)
    raise Exception("Too many connection errors.")

# Access Token
def get_token():
    resp = safe_request('post', TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret
    })
    resp.raise_for_status()
    return resp.json()["access_token"]

# User data (ID and cursus level)
def get_user_data(username, headers):
    resp = safe_request('get', f"{API_BASE}/users/{username}", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    
    level = None
    for cursus in data.get("cursus_users", []):
        if cursus.get("cursus_id") == 21:
            level = cursus.get("level")
            time.sleep(1)
            break
    return data["id"], level

# Get evals that a given user did to others
def get_given_evaluations(user_id, headers):
    page = 1
    all_evals = []
    while True:
        resp = safe_request(
            'get',
            f"{API_BASE}/scale_teams",
            headers=headers,
            params={
                "filter[user_id]": user_id,
                "page[size]": 100,
                "page[number]": page
            }
        )
        if resp.status_code != 200:
            print(f"{Color.RED}Error HTTP {resp.status_code}: {resp.text}{Color.RESET}")
            break

        data = resp.json()
        if not data:
            break

        all_evals.extend(data)
        page += 1
        time.sleep(1)

    return all_evals

# Process the evaluations and store in the structure
def process_evaluations(evals, evaluator, headers):
    if evaluator not in user_levels:
        try:
            _, level = get_user_data(evaluator, headers)
            user_levels[evaluator] = level
        except:
            user_levels[evaluator] = None

    eval_level = user_levels[evaluator]
    if eval_level is None:
        return

    for e in evals:

        final_mark = e.get("final_mark")

        team = e.get("team", {})
        project_name = "Desconocido"

        if "project" in team and isinstance(team["project"], dict):
            project_name = team["project"].get("name", "Desconocido")
        elif "project_gitlab_path" in team:
            # path as project name, possible solution
            project_name = team["project_gitlab_path"].split("/")[-1]

        cursus_id = e.get("cursus_id", "N/A")
        
        # new filter for cursus
        if any(keyword in project_name for keyword in ["piscine", "rush", "exam", "shell-","c-"]):
            continue

        for user in e.get("correcteds", []):
            evaluated = user.get("login")

            if evaluated and evaluated != evaluator:
                if evaluated not in user_levels:
                    try:
                        _, level = get_user_data(evaluated, headers)
                        user_levels[evaluated] = level
                    except:
                        user_levels[evaluated] = None

                level = user_levels[evaluated]
                if level is None:
                    continue

                if final_mark is not None:
                    delta = 1 if final_mark >= 100 else -1
                    evaluations_map[evaluator][evaluated] += delta
                    print(f"{Color.CYAN} Evaluated: {evaluated}, Final grade: {final_mark}{Color.RESET}")
                else:
                   print(f"{Color.YELLOW}   Without final grade {evaluated} (Proyect: '{project_name}', Cursus ID: {cursus_id}){Color.RESET}")

# Export the alerts if there are any
def export_alerts_report():
    wb = Workbook()
    ws = wb.active
    ws.title = "Alerts"
    ws.append([
        "Evaluator", "Evaluator Level",
        "Evaluated", "Evaluated Level",
        "Number of Evaluations", "% of Total", "Adjusted"
    ])

    count = 0
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    for evaluator, counter in evaluations_map.items():
        eval_level = user_levels.get(evaluator)
        if eval_level is None:
            continue

        threshold = 3 if eval_level <= 2 else round(eval_level - 1)
        total_evals = sum(abs(v) for v in counter.values())

        for evaluated, times in counter.items():
            if times <= 1:
                continue

            porcentaje = times / total_evals if total_evals > 0 else 0
            if total_evals > 11:
                penalizacion = 5 if porcentaje > 0.10 else -2
            else:
                penalizacion = 0;

            adjusted_times = times + penalizacion

            if adjusted_times > threshold:
                level_corrected = user_levels.get(evaluated)

                if level_corrected is None:
                    try:
                        _, lvl = get_user_data(evaluated, headers)
                        user_levels[evaluated] = lvl
                        level_corrected = lvl
                    except:
                        level_corrected = "N/A"

                ws.append([
                    evaluator, eval_level,
                    evaluated, level_corrected,
                    times, f"{porcentaje:.0%}", adjusted_times
                ])
                count += 1

    if count > 0:
        wb.save(DESTINY_FILE)
        print(f"\n{Color.RED}{count} alerts registered in doc {Color.RESET}")
    else:
        print(f"\n{Color.GREEN}No alerts. No one in the group had any suspicious behaviour{Color.RESET}")

# MAIN 
def main():
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        with open(ORIGIN_FILE, "r", encoding="utf-8") as f:
            logins = [line.strip() for line in f if line.strip()]

        for login in logins:
            print(f"{Color.GREEN}Procesing '{login}'…{Color.RESET}")
            try:
                user_id, level = get_user_data(login, headers)
                time.sleep(1)
                user_levels[login] = level
                if level is not None:
                    print(f"{Color.WHITE}   Level: {level:.2f}{Color.RESET}")
                else:
                    print(f"{Color.YELLOW}   Level not found{Color.RESET}")

                evals = get_given_evaluations(user_id, headers)
                process_evaluations(evals, login, headers)
            except requests.exceptions.HTTPError as e:
                print(f"{Color.RED} Error with '{login}': {e}{Color.RESET}")

        export_alerts_report()

    except Exception as ex:
        print(f"{Color.RED} General Error: {ex}{Color.RESET}")

if __name__ == "__main__":
    main()
