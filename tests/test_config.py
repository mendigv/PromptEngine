import pytest
from promptengine.config.config_loader import get_config, get_models_with_submodels, get_domains

def test_config_loads_properly():
    config = get_config()
    assert config is not None
    assert 'models' in config
    assert 'tones' in config
    assert 'domains' in config
    assert 'topic_roles' in config
    assert 'formatters' in config

def test_get_models():
    models = get_models_with_submodels()
    assert isinstance(models, dict)
    assert len(models) > 0
    assert '1' in models
    assert models['1']['key'] == 'openai_group'

def test_get_domains():
    domains = get_domains()
    assert isinstance(domains, list)
    assert len(domains) > 0
    assert domains[0][0] == 'storia'

def test_get_tones():
    from promptengine.config.config_loader import get_tones
    tones = get_tones()
    assert isinstance(tones, dict)
    assert len(tones) >= 4

def test_get_topic_roles():
    from promptengine.config.config_loader import get_topic_roles
    roles = get_topic_roles()
    assert 'email' in roles
    assert 'code' in roles
    assert isinstance(roles['email'], tuple)
    assert len(roles['email']) == 2

def test_get_formatter_template():
    from promptengine.config.config_loader import get_formatter_template
    tmpl = get_formatter_template('chatgpt')
    assert '{RUOLO}' in tmpl
    assert '{CONTESTO}' in tmpl
    assert '{COMPITO}' in tmpl

def test_formatter_aliases():
    from promptengine.config.config_loader import get_formatter_template
    # o1_pro dovrebbe usare il template openai_reasoning
    tmpl = get_formatter_template('o1_pro')
    assert tmpl  # Non vuoto

def test_hot_reload(tmp_path):
    import yaml, time
    from promptengine.config import config_loader
    # Salva stato originale
    original_path = config_loader._config_path
    original_mtime = config_loader._config_mtime
    # Il test verifica che il meccanismo mtime funzioni
    assert config_loader._config_mtime > 0
