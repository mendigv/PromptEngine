"""Gestione della comunicazione HTTP con FastAPI e stato sessione locale."""

import os
import json
import sys
import re
from typing import Dict, Any, Optional, Tuple

import requests
from requests.exceptions import ConnectionError as ReqConnectionError, Timeout, RequestException

from promptengine.ui.ansi_colors import C

API_BASE_URL = "http://127.0.0.1:8421"
API_TIMEOUT  = 15

LOGGED_IN_USER: Optional[str] = None
SESSION_TOKEN: Optional[str] = None
REFRESH_TOKEN: Optional[str] = None
SESSION_FILE = os.path.expanduser('~/.promptengine_session.json')

def is_valid_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

def save_session(email: str, token: str, refresh_token: str = None) -> None:
    try:
        data = {'email': email, 'token': token}
        if refresh_token:
            data['refresh_token'] = refresh_token
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
        if sys.platform != 'win32':
            os.chmod(SESSION_FILE, 0o600)
    except OSError:
        pass

def load_session() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            return data.get('email'), data.get('token'), data.get('refresh_token')
    except (OSError, ValueError):
        return None, None, None

def clear_session() -> None:
    try:
        os.remove(SESSION_FILE)
    except OSError:
        pass

def _post(endpoint: str, payload: Dict[str, Any], _retry: bool = True) -> Optional[requests.Response]:
    """Esegue una POST al backend e gestisce errori di rete generici."""
    global SESSION_TOKEN, REFRESH_TOKEN
    
    headers = {}
    if SESSION_TOKEN:
        headers['Authorization'] = f"Bearer {SESSION_TOKEN}"

    try:
        r = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT,
        )
        # Auto-refresh on 401
        if r.status_code == 401 and _retry and REFRESH_TOKEN:
            refresh_resp = requests.post(
                f"{API_BASE_URL}/api/refresh-token",
                json={'refresh_token': REFRESH_TOKEN},
                timeout=API_TIMEOUT,
            )
            if refresh_resp.status_code == 200:
                data = refresh_resp.json()
                SESSION_TOKEN = data.get('session_token')
                REFRESH_TOKEN = data.get('refresh_token')
                # Persist new tokens
                if LOGGED_IN_USER:
                    save_session(LOGGED_IN_USER, SESSION_TOKEN, REFRESH_TOKEN)
                # Retry original request with new token
                return _post(endpoint, payload, _retry=False)
        return r
    except ReqConnectionError:
        print(f'\n  {C.RED}✗ Impossibile connettersi al server ({API_BASE_URL}).{C.RESET}')
        print(f'  {C.GRAY}Assicurati che il backend sia avviato con:{C.RESET}')
        print(f'  {C.YELLOW}  uvicorn server:app --host 127.0.0.1 --port 8421{C.RESET}')
        return None
    except Timeout:
        print(f'\n  {C.RED}✗ Timeout: il server non risponde entro {API_TIMEOUT}s.{C.RESET}')
        return None
    except RequestException as exc:
        print(f'\n  {C.RED}✗ Errore di rete: {exc}{C.RESET}')
        return None

def api_register(email: str, password: str) -> Optional[requests.Response]:
    return _post('/api/register', {'email': email, 'password': password})

def api_verify_totp(email: str, totp_token: str) -> Optional[requests.Response]:
    return _post('/api/verify-totp', {'email': email, 'totp_token': totp_token})

def api_login(email: str, password: str, totp_token: str) -> Optional[requests.Response]:
    return _post('/api/login', {'email': email, 'password': password, 'totp_token': totp_token})

def api_generate_response(prompt: str, model: str = "groq/llama-3.1-8b-instant") -> Optional[requests.Response]:
    return _post('/api/generate-response', {'prompt': prompt, 'model': model})

def api_refresh_token(refresh_tok: str) -> Optional[requests.Response]:
    return _post('/api/refresh-token', {'refresh_token': refresh_tok})
