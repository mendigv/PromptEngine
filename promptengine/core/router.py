"""Routing logic for prompts, domain/topic detection, and formatting for AI."""

import re
from typing import Tuple, Dict, Any, Optional

from promptengine.config.models_config import DOMAINS, TOPIC_ROLES, TONE_INSTRUCTIONS
from promptengine.config.config_loader import (
    get_topic_contexts, get_topic_tasks, get_formatter_template,
    get_midjourney_styles, get_topic_detection_rules, get_domains
)

# ── Domain e Topic Detection ──────────────────────────────────────────────────

def detect_domain(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Detects the domain using TF-IDF in-process (no HTTP)."""
    from promptengine.engine import detect_domain_local
    domain, role, _ = detect_domain_local(text)
    return domain, role

def detect_topic(text: str, ai: str) -> str:
    t = text.lower().strip()
    if ai == 'midjourney':
        return 'image'
    rules = get_topic_detection_rules()
    for topic, patterns in rules.items():
        for p in patterns:
            if re.search(p, t):
                return topic
    return 'general'

# ── Builders ──────────────────────────────────────────────────────────────────

def build_role_string(topic: str, user_text: str) -> str:
    core, skills = TOPIC_ROLES.get(topic, TOPIC_ROLES['general'])
    if topic in ('explain', 'general'):
        _, domain_role = detect_domain(user_text)
        if domain_role:
            core = domain_role
    return f"{core}. Key skills: {skills}."

def build_protected_context(user_text: str, topic: str, ai: str) -> str:
    trimmed = user_text.strip()
    wc = len(trimmed.split())
    complexity = 'detailed and articulate' if wc > 50 else ('clear and specific' if wc > 20 else 'concise')
    
    ctx_templates = get_topic_contexts()
    template = ctx_templates.get(topic, ctx_templates.get('general', ''))
    context = template.format(complexity=complexity, trimmed=trimmed)
    
    return context

def build_protected_tone(tone: str, ai: str) -> str:
    ti = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS['formale'])
    s, a = ti['style'], ti['avoid']
    return f"Required style: {s}\nStrictly avoid: {a}"

def build_caged_task(user_text: str, topic: str, ai: str) -> str:
    task_templates = get_topic_tasks()
    task_text = task_templates.get(topic, task_templates.get('general', '')).format(user_text=user_text)

    # Force language matching
    task_text += "\n\nCRITICAL: Respond in the exact same language as the user's raw prompt. If the prompt is in English, all formatting, tables, and responses MUST be in English. Do NOT output Italian unless the prompt is in Italian."

    if ai in ('llama4', 'gemma'):
        task_text += "\n\nStart each paragraph of the 5 steps with the explicit tag ### STEP X. Failing to include the tag will invalidate the execution."

    if ai in ('gemma', 'llama4', 'mistral', 'qwen', 'cohere', 'perplexity', 'grok'):
        task_text += "\n\n=== STRUCTURED FORMATTING EXAMPLE ===\n### Step 1 - Analysis\n[Your analytical text here...]\n\n### Step 2 - Execution\n[Your direct text here...]\n(Continue strictly following this formatting, omitting the text in square brackets)"

    if ai in ('deepseek_r1', 'o1_pro', 'o3_mini', 'gemini_3_5_reasoning'):
        task_text = re.sub(r'Passo \d+ — [^\n]*\n', '', task_text)
        task_text += "\n\n[IMPORTANT: Perform your reasoning internally without showing intermediate steps. Produce the final output directly following the remaining constraints.]"

    return task_text

def build_midjourney(user_text: str, tone: str) -> str:
    idea = user_text.strip()
    styles = get_midjourney_styles()
    art, light, mood, ratio = styles.get(tone, styles.get('formale', ('', '', '', '')))
    prompt_str = f'{idea[:100]}, {art}, {light}, {mood}, 8K resolution, hyperrealistic masterpiece, award-winning photography {ratio} --v 6.1 --style raw --q 2 --s 750 --no blur, watermark, text'
    return f"""[MIDJOURNEY PROFESSIONAL VISUAL PROMPT]

=== CONCEPT ===
Idea visiva: "{idea}"

=== STILE ARTISTICO ===
{art}

=== ILLUMINAZIONE ===
{light}

=== MOOD E ATMOSFERA ===
{mood}

=== PARAMETRI TECNICI ===
Camera: Hasselblad H6D-100c, 85mm f/2.8
ISO: 100 | Color grading: Cinematic LUT, film grain 15%

=== ASPECT RATIO ===
{ratio.replace('--ar ', '')} | Qualità: --q 2

─────────────────────────────────────────
STRINGA PRONTA PER MIDJOURNEY:
/imagine prompt: {prompt_str}"""

# ── Formatters per AI specifiche ──────────────────────────────────────────────

def format_prompt(ai: str, vars: Dict[str, str]) -> str:
    template = get_formatter_template(ai)
    return template.format(**vars)

# ── Entrypoint del Router ─────────────────────────────────────────────────────

def build_prompt(user_text: str, ai: str, tone: str) -> str:
    if ai == 'midjourney':
        return build_midjourney(user_text, tone)

    topic = detect_topic(user_text, ai)

    prompt_vars = {
        'RUOLO': build_role_string(topic, user_text),
        'CONTESTO': build_protected_context(user_text, topic, ai),
        'COMPITO': build_caged_task(user_text, topic, ai),
        'TONO_PROTETTO': build_protected_tone(tone, ai)
    }

    return format_prompt(ai, prompt_vars)
