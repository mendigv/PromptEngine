import pytest
from promptengine.core.router import detect_topic, build_prompt

def test_detect_topic():
    # Should fallback to regex if ai is not midjourney
    assert detect_topic("fammi un riassunto", "chatgpt") == "summary"
    assert detect_topic("scrivi una mail al capo", "claude_3_5") == "email"
    assert detect_topic("scrivi un codice in python", "chatgpt") == "code"
    
    # Midjourney always returns 'image'
    assert detect_topic("disegna un gatto", "midjourney") == "image"
    assert detect_topic("random text", "midjourney") == "image"

def test_build_prompt_basic():
    # Test basic prompt formatting
    prompt = build_prompt("spiegami la rivoluzione francese", "chatgpt", "formale")
    assert "Sei un" in prompt
    assert "formale" in prompt.lower()
    assert "rivoluzione francese" in prompt.lower()

def test_build_prompt_midjourney():
    prompt = build_prompt("un gatto astronauta", "midjourney", "creativo")
    assert "/imagine prompt" in prompt
    assert "gatto astronauta" in prompt

def test_detect_topic_translation():
    assert detect_topic("traduci in inglese questo testo", "chatgpt") == "translation"

def test_detect_topic_strategy():
    assert detect_topic("analizza il mercato e pianifica una strategia", "chatgpt") == "strategy"

def test_build_prompt_returns_string():
    prompt = build_prompt("scrivi un codice python per ordinare una lista", "chatgpt", "tecnico")
    assert isinstance(prompt, str)
    assert len(prompt) > 100

def test_build_prompt_deepseek():
    prompt = build_prompt("spiegami la relatività", "deepseek_r1", "tecnico")
    assert isinstance(prompt, str)
    assert 'ragionamento' in prompt.lower() or 'reasoning' in prompt.lower() or 'internamente' in prompt.lower()

def test_build_prompt_midjourney():
    prompt = build_prompt("un gatto astronauta", "midjourney", "creativo")
    assert '/imagine prompt' in prompt
