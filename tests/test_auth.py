import pytest
from server import create_jwt, create_refresh_token, verify_jwt
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException
import jwt
import time
from datetime import datetime, timedelta

def test_create_and_verify_jwt():
    email = "test@example.com"
    token = create_jwt(email)
    
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    extracted_email = verify_jwt(cred)
    
    assert extracted_email == email

def test_create_refresh_token():
    email = "test@example.com"
    token = create_refresh_token(email)
    
    from server import JWT_REFRESH_SECRET, JWT_ALGORITHM
    payload = jwt.decode(token, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
    
    assert payload["sub"] == email
    assert payload["type"] == "refresh"
    assert "exp" in payload

def test_verify_jwt_expired():
    from server import JWT_SECRET, JWT_ALGORITHM
    
    # Create expired token
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "test@example.com", "exp": expire}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    with pytest.raises(HTTPException) as excinfo:
        verify_jwt(cred)
    assert excinfo.value.status_code == 401
    assert "Token scaduto" in excinfo.value.detail

from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_refresh_token_has_correct_type():
    from server import create_refresh_token, JWT_REFRESH_SECRET, JWT_ALGORITHM
    token = create_refresh_token("test@example.com")
    payload = jwt.decode(token, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["type"] == "refresh"

def test_refresh_token_endpoint():
    from server import create_refresh_token
    refresh = create_refresh_token("test@example.com")
    resp = client.post("/api/refresh-token", json={"refresh_token": refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    assert "refresh_token" in data
    assert data["status"] == "refreshed"

def test_refresh_with_invalid_token():
    resp = client.post("/api/refresh-token", json={"refresh_token": "invalid.token.here"})
    assert resp.status_code == 401

def test_password_minimum_length():
    """La password deve essere di almeno 8 caratteri."""
    resp = client.post("/api/register", json={"email": "short@test.com", "password": "abc1234"})
    assert resp.status_code == 422  # Validation error
