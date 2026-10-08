import pytest
from fastapi.testclient import TestClient
from server import app, init_ml_models

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_ml():
    init_ml_models()

def test_detect_domain_smart_tfidf():
    resp = client.post("/api/detect-domain-smart", json={"text": "parlami della rivoluzione francese e di napoleone"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "storia"
    # Il metodo può essere tfidf o llm-groq, entrambi validi
    assert data["method"] in ("tfidf", "llm-groq")
    assert data["confidence"] > 0

def test_detect_domain_smart_low_confidence():
    # Testo ambiguo che fallisce il TF-IDF (sotto 0.40) ma Groq non ha chiave in test, quindi fallback-failed-no-key
    resp = client.post("/api/detect-domain-smart", json={"text": "ciao come stai"})
    assert resp.status_code == 200
    data = resp.json()
    # If the confidence was low and no GROQ_API_KEY is available (or it fails), it should return none or fallback-failed
    assert data["method"] in ("none", "fallback-failed-no-key")
    assert data["confidence"] == 0.0
