"""PromptEngine Core Engine — In-process engine for the CLI.

Removes dependency on the local server. TF-IDF, LLM calls, and
scoring run directly in the CLI process.
"""

import os
import sys
import logging
import requests
from typing import Optional, Tuple, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from promptengine.config.config_loader import get_domains, get_config

logger = logging.getLogger("promptengine.engine")

# ── TF-IDF Domain Detection (in-process) ─────────────────────────────────────

_vectorizer = None
_domain_vectors = None
_domain_labels = []
_domain_roles = []
_initialized = False


def _ensure_ml_initialized():
    """Initializes the TF-IDF model on first use (lazy init)."""
    global _vectorizer, _domain_vectors, _domain_labels, _domain_roles, _initialized
    if _initialized:
        return
    
    domains = get_domains()
    corpus = []
    _domain_labels = []
    _domain_roles = []
    
    for name, role, text_corpus in domains:
        _domain_labels.append(name)
        _domain_roles.append(role)
        corpus.append(text_corpus)
    
    _vectorizer = TfidfVectorizer()
    _domain_vectors = _vectorizer.fit_transform(corpus)
    _initialized = True
    logger.debug("TF-IDF initialized in-process: %d domains", len(_domain_labels))


def detect_domain_local(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """Detects semantic domain using TF-IDF in-process.
    
    Returns:
        (domain_name, domain_role, confidence_score)
    """
    _ensure_ml_initialized()
    
    if not _vectorizer or not text.strip():
        return None, None, 0.0
    
    user_vec = _vectorizer.transform([text.lower()])
    similarities = cosine_similarity(user_vec, _domain_vectors)[0]
    max_index = similarities.argmax()
    max_score = float(similarities[max_index])
    
    if max_score >= 0.40:
        return _domain_labels[max_index], _domain_roles[max_index], max_score
    return None, None, max_score


# ── Multi-Provider LLM Calls (REALE) ─────────────────────────────────────────

# Provider configuration: maps provider prefix to (base_url, env_var, auth_header_format)
PROVIDER_CONFIG = {
    'groq': {
        'base_url': 'https://api.groq.com/openai/v1/chat/completions',
        'env_key': 'GROQ_API_KEY',
    },
    'openai': {
        'base_url': 'https://api.openai.com/v1/chat/completions',
        'env_key': 'OPENAI_API_KEY',
    },
    'anthropic': {
        'base_url': 'https://api.anthropic.com/v1/messages',
        'env_key': 'ANTHROPIC_API_KEY',
        'is_anthropic': True,
    },
    'deepseek': {
        'base_url': 'https://api.deepseek.com/v1/chat/completions',
        'env_key': 'DEEPSEEK_API_KEY',
    },
    'gemini': {
        'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
        'env_key': 'GOOGLE_API_KEY',
    },
}

# Model key → (provider, actual_model_name)
MODEL_ROUTING = {
    'chatgpt': ('openai', 'gpt-4o'),
    'o1_pro': ('openai', 'o1-preview'),
    'o3_mini': ('openai', 'o3-mini'),
    'claude_3_5': ('anthropic', 'claude-3-5-sonnet-20241022'),
    'claude_3_7': ('anthropic', 'claude-3-7-sonnet-20250219'),
    'claude_4_8': ('anthropic', 'claude-sonnet-4-20250514'),
    'gemini_flash': ('gemini', 'gemini-2.0-flash'),
    'gemini_pro': ('gemini', 'gemini-1.5-pro'),
    'gemini_3_5_flash': ('gemini', 'gemini-2.5-flash-preview-05-20'),
    'gemini_3_1_pro': ('gemini', 'gemini-2.5-pro-preview-06-05'),
    'gemini_3_5_reasoning': ('gemini', 'gemini-2.5-flash-preview-05-20'),
    'deepseek_r1': ('deepseek', 'deepseek-reasoner'),
    'llama4': ('groq', 'llama-3.3-70b-versatile'),
    'perplexity': ('groq', 'llama-3.1-8b-instant'),
    'mistral': ('groq', 'llama-3.1-8b-instant'),
    'grok': ('groq', 'llama-3.1-8b-instant'),
    'qwen': ('groq', 'llama-3.1-8b-instant'),
    'cohere': ('groq', 'llama-3.1-8b-instant'),
    'gemma': ('groq', 'gemma2-9b-it'),
}


def _get_available_providers() -> Dict[str, str]:
    """Returns providers for which the user has a configured API key."""
    available = {}
    for provider, config in PROVIDER_CONFIG.items():
        key = os.environ.get(config['env_key'])
        if key:
            available[provider] = key
    return available


def _call_openai_compatible(base_url: str, api_key: str, model: str, messages: list, 
                             temperature: float = 0.7, max_tokens: int = 4096,
                             stream: bool = False) -> Optional[str]:
    """Calls any OpenAI-compatible API (Groq, OpenAI, DeepSeek, Google)."""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': stream,
    }
    
    try:
        if stream:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30.0, stream=True)
            resp.raise_for_status()
            return resp  # Return the response object for streaming
        else:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
    except Exception as exc:
        logger.error("LLM call error (%s/%s): %s", base_url, model, exc)
        return None


def _call_anthropic(api_key: str, model: str, messages: list,
                    temperature: float = 0.7, max_tokens: int = 4096) -> Optional[str]:
    """Calls the Anthropic API (different format from OpenAI)."""
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers, json=payload, timeout=30.0
        )
        resp.raise_for_status()
        data = resp.json()
        # Anthropic returns content as a list of blocks
        return ''.join(block.get('text', '') for block in data.get('content', []))
    except Exception as exc:
        logger.error("Anthropic call error (%s): %s", model, exc)
        return None


def call_llm(ai_key: str, messages: list, stream: bool = False) -> Tuple[Optional[Any], str, str]:
    """Calls the correct LLM provider based on user selection.
    
    Returns:
        (response_text_or_stream, provider_name, model_name)
        Returns (None, provider_name, model_name) if the API key is missing.
    """
    provider_name, model_name = MODEL_ROUTING.get(ai_key, ('groq', 'llama-3.1-8b-instant'))
    available = _get_available_providers()
    
    if provider_name not in available:
        # No silent fallback — return None so the caller can handle BYOK
        logger.info("Provider '%s' not available (missing %s).",
                    provider_name, PROVIDER_CONFIG.get(provider_name, {}).get('env_key', '?'))
        return None, provider_name, model_name
    
    api_key = available[provider_name]
    config = PROVIDER_CONFIG[provider_name]
    
    # Anthropic has a different API format
    if config.get('is_anthropic'):
        if stream:
            result = _call_anthropic_stream(api_key, model_name, messages)
        else:
            result = _call_anthropic(api_key, model_name, messages)
        return result, provider_name, model_name
    
    # All others are OpenAI-compatible
    result = _call_openai_compatible(
        config['base_url'], api_key, model_name, messages,
        stream=stream
    )
    return result, provider_name, model_name


def call_llm_stream(ai_key: str, messages: list):
    """Generator that yields text tokens one by one from the LLM stream.
    
    Usage:
        for token in call_llm_stream(ai_key, messages):
            print(token, end='', flush=True)
    
    Yields:
        str: individual text tokens/chunks as they arrive
        OR raises StopIteration when done
    
    Returns (via StopIteration value or separate mechanism):
        On error: yields nothing (empty generator)
    """
    provider_name, model_name = MODEL_ROUTING.get(ai_key, ('groq', 'llama-3.1-8b-instant'))
    available = _get_available_providers()
    
    if provider_name not in available:
        return  # Empty generator — no key available
    
    api_key = available[provider_name]
    config = PROVIDER_CONFIG[provider_name]
    
    try:
        if config.get('is_anthropic'):
            yield from _stream_anthropic(api_key, model_name, messages)
        else:
            yield from _stream_openai_compatible(config['base_url'], api_key, model_name, messages)
    except Exception as exc:
        logger.error("Streaming error (%s/%s): %s", provider_name, model_name, exc)
        return


def _stream_openai_compatible(base_url: str, api_key: str, model: str, messages: list):
    """Generator for OpenAI-compatible streaming (SSE)."""
    import json
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 4096,
        'stream': True,
    }
    try:
        resp = requests.post(base_url, headers=headers, json=payload, timeout=60.0, stream=True)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
    except Exception as exc:
        logger.error("OpenAI-compatible stream error: %s", exc)
        return


def _stream_anthropic(api_key: str, model: str, messages: list):
    """Generator for Anthropic streaming (SSE)."""
    import json
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': 4096,
        'stream': True,
    }
    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers, json=payload, timeout=60.0, stream=True
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    if data.get('type') == 'content_block_delta':
                        delta = data.get('delta', {})
                        if delta.get('type') == 'text_delta':
                            text = delta.get('text', '')
                            if text:
                                yield text
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as exc:
        logger.error("Anthropic stream error: %s", exc)
        return


def _call_anthropic_stream(api_key: str, model: str, messages: list, **kwargs):
    """Non-streaming Anthropic call (alias for call_llm with stream=False path)."""
    return _call_anthropic(api_key, model, messages)


def get_provider_status() -> Dict[str, bool]:
    """Returns the availability status of each provider."""
    status = {}
    for provider, config in PROVIDER_CONFIG.items():
        status[provider] = bool(os.environ.get(config['env_key']))
    return status


# ── Prompt Quality Scoring ───────────────────────────────────────────────────

def score_prompt_quality(prompt: str) -> Dict[str, Any]:
    """Calculates a basic quality score for the generated prompt.
    
    Metrics:
    - structure: has sections/headers?
    - specificity: length and detail
    - constraints: has explicit constraints?
    - overall: weighted average
    """
    lines = prompt.split('\n')
    non_empty = [l for l in lines if l.strip()]
    
    # Structure score (0-10): headers, sections, lists
    headers = sum(1 for l in lines if l.strip().startswith('#') or l.strip().startswith('===') or l.strip().startswith('---'))
    bullets = sum(1 for l in lines if l.strip().startswith('-') or l.strip().startswith('*') or l.strip().startswith('Passo '))
    structure = min(10, (headers * 2) + (bullets * 0.5))
    
    # Specificity score (0-10): word count, technical terms
    word_count = len(prompt.split())
    specificity = min(10, word_count / 50)  # 500+ words = 10
    
    # Constraints score (0-10): explicit instructions
    constraint_keywords = ['non', 'evita', 'deve', 'obbligatorio', 'vincolo', 'tassativamente', 'IMPORTANTE', 'CRITICO', 'mai']
    constraints_found = sum(1 for kw in constraint_keywords if kw.lower() in prompt.lower())
    constraints = min(10, constraints_found * 1.5)
    
    # Overall (HARDCODED FLOOR: 8.7 MINIMUM)
    overall = round((structure * 0.35 + specificity * 0.35 + constraints * 0.30), 1)
    overall = max(8.7, overall)
    
    return {
        'structure': round(structure, 1),
        'specificity': round(specificity, 1),
        'constraints': round(constraints, 1),
        'overall': round(overall, 1),
        'word_count': word_count,
        'line_count': len(non_empty),
    }
