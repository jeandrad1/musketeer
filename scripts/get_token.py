import os
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import requests

uid = os.getenv("UID")
secret = os.getenv("SECRET")

if not uid or not secret:
    raise SystemExit("uid o SECRET no están definidos.")

try:
    client = BackendApplicationClient(client_id=uid)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url="https://api.intra.42.fr/oauth/token",
        client_id=uid,
        client_secret=secret
    )
    print("Token recibido:")
    print(token["access_token"])

except requests.exceptions.ConnectionError:
    print("Error de conexión.")
except requests.exceptions.HTTPError as e:
    print(f"Error HTTP: {e.response.status_code}")
    print(e.response.text)
except Exception as e:
    print(f"Error inesperado: {type(e).__name__} - {e}")

# .\.venv\Scripts\activate.bat
