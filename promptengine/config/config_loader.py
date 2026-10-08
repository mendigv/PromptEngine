import os
import yaml
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("promptengine.config")

_config: Dict[str, Any] = {}
_config_mtime: float = 0.0
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

def _load_config() -> Dict[str, Any]:
    global _config, _config_mtime
    try:
        mtime = os.path.getmtime(_config_path)
    except OSError:
        logger.error("config.yaml non trovato in: %s", _config_path)
        raise FileNotFoundError(f"File di configurazione non trovato: {_config_path}")
    
    if mtime != _config_mtime or not _config:
        with open(_config_path, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
        _config_mtime = mtime
        # Validazione sezioni obbligatorie
        required = ['models', 'tones', 'domains', 'topic_roles', 'formatters']
        for section in required:
            if section not in _config:
                raise ValueError(f"Sezione obbligatoria '{section}' mancante in config.yaml")
        logger.info("config.yaml caricato/ricaricato (%d modelli, %d toni, %d domini)",
                    len(_config.get('models', {})), len(_config.get('tones', {})), len(_config.get('domains', [])))
    return _config

def get_config() -> Dict[str, Any]:
    return _load_config()

def get_models_with_submodels() -> Dict[str, Dict[str, Any]]:
    config = get_config()
    return config.get('models', {})

def get_models() -> Dict[str, Dict[str, Any]]:
    config = get_config()
    models = config.get('models', {})
    return {k: {k2: v2 for k2, v2 in v.items() if k2 != 'sub_models'} for k, v in models.items()}

def get_tones() -> Dict[str, Dict[str, str]]:
    config = get_config()
    tones = config.get('tones', {})
    return {k: {'key': v['key'], 'name': v['name'], 'desc': v['desc']} for k, v in tones.items()}

def get_tone_instructions() -> Dict[str, Dict[str, str]]:
    config = get_config()
    tones = config.get('tones', {})
    return {v['key']: {'style': v['style'], 'avoid': v['avoid']} for v in tones.values()}

def get_domains() -> List[Tuple[str, str, str]]:
    config = get_config()
    domains = config.get('domains', [])
    return [(d['name'], d['role'], d['corpus']) for d in domains]

def get_topic_roles() -> Dict[str, Tuple[str, str]]:
    config = get_config()
    roles = config.get('topic_roles', {})
    return {k: (v['role'], v['skills']) for k, v in roles.items()}

def get_topic_contexts() -> Dict[str, str]:
    return get_config().get('topic_contexts', {})

def get_topic_tasks() -> Dict[str, str]:
    return get_config().get('topic_tasks', {})

def get_formatter_aliases() -> Dict[str, str]:
    return get_config().get('formatter_aliases', {})

def get_formatter_template(ai_key: str) -> str:
    config = get_config()
    formatters = config.get('formatters', {})
    aliases = config.get('formatter_aliases', {})
    if ai_key in aliases:
        ai_key = aliases[ai_key]
    return formatters.get(ai_key, formatters.get('chatgpt', ''))

def get_midjourney_styles() -> Dict[str, Tuple[str, str, str, str]]:
    styles = get_config().get('midjourney_styles', {})
    return {k: (v['art'], v['light'], v['mood'], v['ratio']) for k, v in styles.items()}

def get_topic_detection_rules() -> Dict[str, List[str]]:
    return get_config().get('topic_detection_rules', {})
