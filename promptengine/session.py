"""User session management with clean encapsulation."""

import os
import json
import sys
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("promptengine.session")

import pathlib
_SESSION_DIR = pathlib.Path.home() / ".promptengine"
SESSION_FILE = str(_SESSION_DIR / "session.json")


@dataclass
class Session:
    """Represents an active user session."""
    email: Optional[str] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    
    @property
    def is_authenticated(self) -> bool:
        return bool(self.email and self.token)
    
    def save(self) -> None:
        """Persists the session to disk."""
        try:
            data = {
                'email': self.email,
                'token': self.token,
                'refresh_token': self.refresh_token,
            }
            _SESSION_DIR.mkdir(exist_ok=True)
            with open(SESSION_FILE, 'w') as f:
                json.dump(data, f)
            if sys.platform != 'win32':
                os.chmod(SESSION_FILE, 0o600)
            logger.debug("Session saved for %s", self.email)
        except OSError as e:
            logger.warning("Failed to save session: %s", e)
    
    @classmethod
    def load(cls) -> 'Session':
        """Loads the session from disk."""
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            return cls(
                email=data.get('email'),
                token=data.get('token'),
                refresh_token=data.get('refresh_token'),
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return cls()
    
    def clear(self) -> None:
        """Clears the current session and the file."""
        self.email = None
        self.token = None
        self.refresh_token = None
        try:
            os.remove(SESSION_FILE)
        except OSError:
            pass
    
    def update_tokens(self, token: str, refresh_token: Optional[str] = None) -> None:
        """Updates tokens and saves."""
        self.token = token
        if refresh_token:
            self.refresh_token = refresh_token
        self.save()


# Global singleton — but encapsulated
current_session = Session()
