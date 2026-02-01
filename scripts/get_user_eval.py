import requests
import os
import time
import sys
import numpy as np
from collections import defaultdict, Counter

API_BASE = "https://api.intra.42.fr/v2"
TOKEN_URL = f"{API_BASE}/oauth/token"

uid = os.getenv("UID")
secret = os.getenv("SECRET")

# Colors
class Color:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

# Structs
evaluations_map = defaultdict(Counter)  # evaluator-> {evaluated -> times}
user_levels = {}  # login -> level


# Safe request with delays and rate limit handling
def safe_request(method, url, headers=None, params=None, data=None, retries=5, delay=3):
    for attempt in range(retries):
        try:
            response = None
            if method.lower() == 'get':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method.lower() == 'post':
                response = requests.post(url, headers=headers, data=data, timeout=15)
            else:
                raise ValueError("Unsupported HTTP method")

            # Handling of rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", delay))
                print(f"{Color.YELLOW}   Rate limit hit. Waiting {retry_after} seconds...{Color.RESET}")
                time.sleep(retry_after)
                continue  # Retry the request

            response.raise_for_status()  # Error for 4xx and 5xx responses
            return response

        except requests.exceptions.RequestException as e:
            print(f"{Color.YELLOW}   Reattempt {attempt + 1}/{retries} due to connection error: {e}{Color.RESET}")
            time.sleep(delay * (attempt + 1)) # Increment the delay with each try

    raise Exception("API request failed after multiple retries.")


# Obtain access token
def get_token():
    resp = safe_request('post', TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": uid,
        "client_secret": secret
    })
    return resp.json()["access_token"]


# User data (ID and cursus level)
def get_user_data(username, headers):
    resp = safe_request('get', f"{API_BASE}/users/{username}", headers=headers)
    data = resp.json()

    level = None
    for cursus in data.get("cursus_users", []):
        if cursus.get("cursus_id") == 21:  # Cursus 42
            level = cursus.get("level")
            break
    return data.get("id"), level


# Get evals that the user has received from others
def get_received_evaluations(user_id, headers):
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
        data = resp.json()
        if not data:
            break

        all_evals.extend(data)
        page += 1
        time.sleep(0.5)  # small delay between pages
    return all_evals


# Process received evaluations for counting
def process_received_evaluations(evals, evaluated, headers):
    if evaluated not in user_levels:
        try:
            _, level = get_user_data(evaluated, headers)
            user_levels[evaluated] = level
        except requests.exceptions.HTTPError:
            user_levels[evaluated] = None

    eval_level = user_levels[evaluated]
    if eval_level is None:
        print(f"{Color.YELLOW}Could not determine level for {evaluated}. Skipping processing.{Color.RESET}")
        return

    for e in evals:
        final_mark = e.get("final_mark")
        corrector = e.get("corrector", {})
        evaluator_login = corrector.get("login")

        # Extract project name for logging
        project_name = "N/A"
        team = e.get("team")
        if team and team.get("project") and team["project"].get("name"):
            project_name = team["project"]["name"]
        
        print(f"   Evaluated by: {evaluator_login or 'Unknown'} | Project: {project_name} | Mark: {final_mark}")

        if not evaluator_login or evaluator_login == evaluated:
            continue

        if evaluator_login not in user_levels:
            try:
                _, lvl = get_user_data(evaluator_login, headers)
                user_levels[evaluator_login] = lvl
            except requests.exceptions.HTTPError:
                user_levels[evaluator_login] = None

        if final_mark is not None:
            delta = 1 if final_mark >= 100 else -1
            evaluations_map[evaluated][evaluator_login] += delta


def check_alerts(login):
    alerts_found = False
    for evaluated, counter in evaluations_map.items():
        eval_level = user_levels.get(evaluated)
        if eval_level is None:
            continue

        threshold = 3 if eval_level <= 2 else round(eval_level - 1)
        total_evals = sum(abs(v) for v in counter.values())
        
        if total_evals == 0:
            continue

        # Formula for alert detection
        evaluators = list(counter.keys())
        values = np.array(list(counter.values()))
        percentages = values / total_evals if total_evals > 0 else np.zeros_like(values)
        
        penalties = np.where(total_evals > 11, np.where(percentages > 0.10, 5, -2), 0)
        adjusted_values = values + penalties

        mask = adjusted_values > threshold
        if np.any(mask):
            alerts_found = True
            print(f"\n{Color.CYAN}--- Alerts for {evaluated} (Lvl {eval_level:.2f}) ---{Color.RESET}")
            
            for i in np.where(mask)[0]:
                evaluator = evaluators[i]
                evaluator_lvl = user_levels.get(evaluator)
                lvl_str = f"{evaluator_lvl:.2f}" if evaluator_lvl is not None else "N/A"
                
                print(f"{Color.RED} ALERT: {evaluator} (Lvl {lvl_str}) "
                      f"gave {values[i]} valids. "
                      f"Adjusted score: {adjusted_values[i]:.2f} (Threshold: {threshold}){Color.RESET}")
                
    if not alerts_found:
        print(f"\n{Color.GREEN}No significant evaluation patterns detected for {login}.{Color.RESET}")

def main():
    if len(sys.argv) != 2:
        print(f"{Color.YELLOW}Usage: python {sys.argv[0]} <login>{Color.RESET}")
        return

    login = sys.argv[1]

    try:
        if not uid or not secret:
            raise ValueError("Environment variables UID and SECRET must be set.")

        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        print(f"{Color.GREEN}Processing '{login}'…{Color.RESET}")
        user_id, level = get_user_data(login, headers)
        user_levels[login] = level
        
        if level is not None:
            print(f"{Color.WHITE}   User Level: {level:.2f}{Color.RESET}")
        else:
            print(f"{Color.YELLOW}   User Level not found for 42 Cursus.{Color.RESET}")

        if not user_id:
            print(f"{Color.RED}User ID for '{login}' not found.{Color.RESET}")
            return

        evals = get_received_evaluations(user_id, headers)
        print(f"{Color.WHITE}   Found {len(evals)} evaluations to process.{Color.RESET}")
        process_received_evaluations(evals, login, headers)

        check_alerts(login)

    except ValueError as ve:
        print(f"{Color.RED}Configuration Error: {ve}{Color.RESET}")
    except requests.exceptions.HTTPError as http_err:
        print(f"{Color.RED}HTTP Error: {http_err.response.status_code} - {http_err}{Color.RESET}")
    except Exception as ex:
        print(f"{Color.RED}An unexpected error occurred: {ex}{Color.RESET}")


if __name__ == "__main__":
    main()