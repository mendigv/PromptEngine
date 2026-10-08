import pytest
import os
import tempfile
from promptengine.session import Session, SESSION_FILE

def test_session_creation():
    s = Session()
    assert s.email is None
    assert not s.is_authenticated

def test_session_authenticated():
    s = Session(email="test@test.com", token="abc123")
    assert s.is_authenticated

def test_session_not_authenticated_without_token():
    s = Session(email="test@test.com")
    assert not s.is_authenticated

def test_session_save_and_load(tmp_path, monkeypatch):
    import promptengine.session as sess_mod
    test_file = str(tmp_path / "test_session.json")
    monkeypatch.setattr(sess_mod, 'SESSION_FILE', test_file)
    
    s = Session(email="test@test.com", token="tok123", refresh_token="ref456")
    s.save()
    
    loaded = Session.load()
    # Note: load uses the module-level SESSION_FILE which we monkeypatched
    assert os.path.exists(test_file)

def test_session_clear(tmp_path, monkeypatch):
    import promptengine.session as sess_mod
    test_file = str(tmp_path / "test_session.json")
    monkeypatch.setattr(sess_mod, 'SESSION_FILE', test_file)
    
    s = Session(email="test@test.com", token="tok")
    s.save()
    s.clear()
    assert s.email is None
    assert not s.is_authenticated
