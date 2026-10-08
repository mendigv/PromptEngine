"""Configurazioni statiche per PromptEngine CLI."""

from typing import Dict, Any, List, Tuple

# ── Modelli AI disponibili ────────────────────────────────────────────────────
from promptengine.config.config_loader import (
    get_models, get_tones, get_domains, get_topic_roles, get_tone_instructions
)

# Retrocompatibilità: stesse variabili esportate
AI_MODELS = get_models()
TONES = get_tones()
DOMAINS = get_domains()
TOPIC_ROLES = get_topic_roles()
TONE_INSTRUCTIONS = get_tone_instructions()
