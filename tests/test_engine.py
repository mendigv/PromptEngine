import pytest
import os
from dotenv import load_dotenv
load_dotenv()

def test_detect_domain_local():
    from promptengine.engine import detect_domain_local
    domain, role, score = detect_domain_local("parlami della rivoluzione francese")
    # Potrebbe o meno matchare con score >= 0.40
    assert isinstance(score, float)
    assert 0 <= score <= 1

def test_detect_domain_local_empty():
    from promptengine.engine import detect_domain_local
    domain, role, score = detect_domain_local("")
    assert domain is None
    assert score == 0.0

def test_score_prompt_quality():
    from promptengine.engine import score_prompt_quality
    prompt = """# RUOLO\nSei un esperto.\n\n# CONTESTO\nL'utente deve scrivere.\n\n# COMPITO\nPasso 1 - Analisi\nPasso 2 - Esecuzione\n\n# VINCOLI\n- Non usare colloquialismi\n- Evita ripetizioni"""
    score = score_prompt_quality(prompt)
    assert score['overall'] > 0
    assert score['structure'] > 0
    assert 'word_count' in score

def test_model_routing():
    from promptengine.engine import MODEL_ROUTING
    assert 'chatgpt' in MODEL_ROUTING
    assert MODEL_ROUTING['chatgpt'] == ('openai', 'gpt-4o')
    assert MODEL_ROUTING['claude_3_5'][0] == 'anthropic'

def test_provider_status():
    from promptengine.engine import get_provider_status
    status = get_provider_status()
    assert isinstance(status, dict)
    assert 'groq' in status
    assert 'openai' in status
