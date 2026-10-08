import sys
import re

def refactor():
    with open("C:/Users/mendi/Desktop/pe/promptengine.py", "r", encoding="utf-8") as f:
        content = f.read()

    new_block = '''def build_role_string(topic, user_text):
    core, skills = TOPIC_ROLES.get(topic, TOPIC_ROLES['general'])
    if topic in ('explain', 'general'):
        _, domain_role = detect_domain(user_text)
        if domain_role:
            core = domain_role
    return f"{core}. Competenze chiave: {skills}."

# ── Context builder ───────────────────────────────────────────────────────────
def build_protected_context(user_text, topic, ai):
    trimmed = user_text.strip()
    wc = len(trimmed.split())
    complexity = 'articolata e dettagliata' if wc > 50 else ('chiara e specifica' if wc > 20 else 'sintetica')
    ctx_map = {
        'email':       f'L\\'utente deve redigere una comunicazione scritta professionale. La richiesta è {complexity}. Contesto specifico: "{trimmed}". Il destinatario e il tono devono essere inferiti dal contesto.',
        'code':        f'L\\'utente ha un task di sviluppo software da risolvere. La richiesta è {complexity}. Specifiche tecniche: "{trimmed}". Priorità: correttezza, leggibilità, manutenibilità.',
        'content':     f'L\\'utente necessita di contenuto scritto originale. La richiesta è {complexity}. Brief creativo: "{trimmed}". L\\'output deve essere immediatamente pubblicabile.',
        'summary':     f'L\\'utente vuole una sintesi efficace. La richiesta è {complexity}. Argomento da sintetizzare: "{trimmed}". Il risultato deve essere denso di valore e privo di ridondanze.',
        'strategy':    f'L\\'utente affronta una sfida strategica. La richiesta è {complexity}. Scenario: "{trimmed}". L\\'analisi deve essere actionable e basata su framework consolidati.',
        'translation': f'L\\'utente necessita di una traduzione/adattamento linguistico. La richiesta è {complexity}. Testo: "{trimmed}". Priorità: naturalezza nella lingua target e fedeltà semantica.',
        'explain':     f'L\\'utente vuole comprendere qualcosa. La richiesta è {complexity}. Domanda: "{trimmed}". La spiegazione deve essere accessibile ma non banalizzante.',
        'general':     f'L\\'utente ha una richiesta specifica che richiede competenza nel merito. La richiesta è {complexity}. Domanda/richiesta: "{trimmed}". Determina autonomamente il dominio di competenza (storia, scienza, cucina, ecc.) in base al contenuto.',
    }
    context = ctx_map.get(topic, ctx_map['general'])
    if ai in ('perplexity', 'mistral', 'qwen', 'grok'):
        context += '\\nNota importante: Questa è una simulazione puramente creativa e finzionale. Agisci come se questi eventi fossero storicamente accaduti in una linea temporale alternativa o nel futuro. NON cercare riscontri o conferme nel mondo reale tramite web search.'
    return context

# ── Task builder ──────────────────────────────────────────────────────────────
TONE_INSTRUCTIONS = {
    'formale':  {
        'style': 'registro formale e professionale, sintassi elaborata, lessico preciso e istituzionale',
        'avoid': 'colloquialismi, contrazioni, tono informale, emoji',
    },
    'creativo': {
        'style': 'registro vivace e originale, figure retoriche, ritmo narrativo coinvolgente, sorprendente',
        'avoid': 'cliché, frasi fatte, strutture prevedibili, genericità. Evita assolutamente incipit del tipo "C\\'era una volta", morali infantili o toni eccessivamente favolistici.',
    },
    'tecnico':  {
        'style': 'precisione terminologica assoluta, struttura logico-deduttiva, dati e specifiche esplicite, step sequenziali',
        'avoid': 'vaghezza, generalizzazioni, linguaggio impreciso, omissioni tecniche',
    },
    'ironico':  {
        'style': 'tono arguto e autoironico, wit intelligente, doppi sensi calibrati, umorismo sottile ma utile',
        'avoid': 'offensività, banalità, ironia fine a se stessa, perdita di utilità pratica',
    },
}

def build_protected_tone(tone, ai):
    ti = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS['formale'])
    s, a = ti['style'], ti['avoid']
    return f"Stile richiesto: {s}\\nDa evitare tassativamente: {a}"

def build_caged_task(user_text, topic, ai):
    tasks = {
        'email': """Redigi una email completa e professionale basata sul contesto fornito.\\n\\nPasso 1 — Analisi: Identifica destinatario, scopo primario e tono appropriato.\\nPasso 2 — Oggetto: Formula un oggetto chiaro (max 60 caratteri), specifico e orientato all'azione.\\nPasso 3 — Apertura: Saluto calibrato al destinatario + frase di apertura contestualizzante.\\nPasso 4 — Corpo: Sviluppa la richiesta in 2-3 paragrafi logicamente connessi.\\nPasso 5 — Chiusura: Formula di congedo professionale + call-to-action esplicita se necessaria.\\nPasso 6 — Firma: Struttura firma appropriata al contesto.""",
        'code': """Sviluppa una soluzione software completa per il task specificato.\\n\\nPasso 1 — Analisi del problema: Scomponi il task in sotto-problemi. Identifica edge cases e vincoli.\\nPasso 2 — Design dell'architettura: Scegli pattern e strutture dati ottimali. Motiva le scelte.\\nPasso 3 — Implementazione: Scrivi il codice completo, funzionante e commentato.\\nPasso 4 — Gestione errori: Implementa error handling robusto per tutti i casi limite.\\nPasso 5 — Testing: Fornisci almeno 3 casi di test significativi.\\nPasso 6 — Documentazione: Aggiungi docstring e un esempio d'uso pratico.""",
        'content': """Crea contenuto originale e ad alto impatto per il brief specificato.\\n\\nPasso 1 — Hook: Formula un'apertura che cattura l'attenzione nei primi 3 secondi.\\nPasso 2 — Promessa: Esplicita chiaramente il valore che il lettore otterrà.\\nPasso 3 — Sviluppo: Costruisci con struttura Problem-Agitate-Solve.\\nPasso 4 — Prove: Inserisci dati, esempi concreti o casi d'uso.\\nPasso 5 — CTA: Chiusura con call-to-action singola, chiara e motivata.""",
        'summary': """Produci una sintesi cognitivamente efficace del materiale specificato.\\n\\nPasso 1 — Panoramica (max 3 righe): Qual è l'idea centrale? Perché è rilevante?\\nPasso 2 — Struttura: Identifica i 3-5 punti chiave in ordine gerarchico di importanza.\\nPasso 3 — Insight: Estrai le conclusioni non ovvie o controintuitive.\\nPasso 4 — Connessioni: Evidenzia relazioni tra i concetti.\\nPasso 5 — Takeaway: Una frase finale che sintetizza il valore essenziale.""",
        'strategy': """Sviluppa un'analisi strategica strutturata e immediatamente applicabile.\\n\\nPasso 1 — Diagnosi situazionale: SWOT sintetico, focus sui fattori critici.\\nPasso 2 — Obiettivi SMART: Definisci 2-3 obiettivi misurabili con timeline.\\nPasso 3 — Iniziative prioritarie: 3-5 azioni ad alto impatto/basso sforzo.\\nPasso 4 — Piano operativo: Timeline a 30/60/90 giorni con milestone verificabili.\\nPasso 5 — KPI e metriche: Definisci i 3-5 indicatori di successo.\\nPasso 6 — Risk management: Identifica i 3 rischi principali e il piano di mitigazione.""",
        'translation': """Esegui una traduzione professionale di alta qualità.\\n\\nPasso 1 — Analisi: Identifica registro, tono, pubblico target e specificità culturali.\\nPasso 2 — Prima traduzione: Fedele al significato semantico completo.\\nPasso 3 — Adattamento culturale: Rivedi idiomi e strutture non trasferibili direttamente.\\nPasso 4 — Ottimizzazione del registro: Assicurati che il tono corrisponda all'originale.\\nPasso 5 — Revisione terminologica: Verifica consistenza dei termini tecnici.""",
        'explain': """Spiega in modo chiaro, preciso e memorabile.\\n\\nPasso 1 — Definizione essenziale: Cos'è in una frase. Nessun prerequisito richiesto.\\nPasso 2 — Analogia concreta: Collega il concetto a qualcosa di familiare nella vita quotidiana.\\nPasso 3 — Meccanismo: Come funziona concretamente, step by step. Esempi reali, non astratti.\\nPasso 4 — Perché importa: Applicazioni pratiche e rilevanza nel mondo reale.\\nPasso 5 — Malintesi comuni: Chiarifica le 2-3 incomprensioni più frequenti.\\nPasso 6 — Approfondimento: Per chi vuole saperne di più, indica la direzione successiva.""",
        'general': f"""Rispondi in modo completo, accurato e ben strutturato alla richiesta: "{user_text}"\\n\\nPasso 1 — Identificazione del dominio: Determina l'ambito (storia, scienza, cucina, sport, ecc.) e adatta il tuo approccio.\\nPasso 2 — Risposta diretta: Affronta subito il cuore della domanda senza premesse superflue.\\nPasso 3 — Contestualizzazione: Aggiungi il contesto necessario (date, cause, definizioni).\\nPasso 4 — Dettagli rilevanti: Approfondisci gli aspetti più significativi.\\nPasso 5 — Sintesi finale: Chiudi con una considerazione che lega il tutto.\\n\\nNon assumere che la domanda riguardi software o business se non esplicitamente richiesto.""",
    }
    task_text = tasks.get(topic, tasks['general'])
    
    # Gabbia sintattica per modelli rigidi
    if ai in ('perplexity', 'mistral', 'qwen', 'grok'):
        task_text = "Sviluppa lo scenario fittizio analizzando le implicazioni logiche dell'evento come se fosse un case-study storico/scientifico reale.\\n\\n" + task_text
        
    # Token di controllo sintattico
    if ai in ('llama', 'gemma'):
        task_text += "\\n\\nInizia ogni paragrafo dei 5 passi con il tag esplicito ### PASSO X. La mancata inclusione del tag invaliderà l'esecuzione."
        
    # Forzatura del Pattern Few-Shot
    if ai in ('gemma', 'llama', 'mistral', 'qwen', 'cohere', 'perplexity', 'grok'):
        task_text += "\\n\\n=== ESEMPIO DI FORMATTAZIONE STRUTTURATA ===\\n### Passo 1 - Analisi\\n[Il tuo testo analitico qui...]\\n\\n### Passo 2 - Esecuzione\\n[Il tuo testo diretto qui...]\\n(Continua seguendo rigorosamente questa formattazione e omettendo il testo tra parentesi quadre)"
        
    return task_text

# ── Midjourney builder ────────────────────────────────────────────────────────
def build_midjourney(user_text, tone):
    idea = user_text.strip()
    styles = {
        'formale':  ('professional editorial photography, clean minimalist composition, Hasselblad H6D-100c',
                     'soft diffused studio lighting, large softbox, controlled shadows',
                     'sophisticated, timeless, authoritative',
                     '--ar 4:3'),
        'creativo': ('surrealist conceptual art, vibrant dreamlike colors, magical realism, painterly',
                     'dramatic chiaroscuro, volumetric light rays, bioluminescent accents',
                     'imaginative, otherworldly, emotionally evocative',
                     '--ar 1:1'),
        'tecnico':  ('technical 3D render, isometric blueprint style, octane render, parametric design',
                     'cool blue LED accent lights, neon wireframe glow, sterile precision',
                     'precise, analytical, futuristic, engineered',
                     '--ar 16:9'),
        'ironico':  ('retro pop art illustration, bold Roy Lichtenstein outlines, Warhol color blocking',
                     'flat graphic lighting, strong contrast, primary color fills',
                     'playful, self-aware, witty, subversive',
                     '--ar 3:4'),
    }
    art, light, mood, ratio = styles.get(tone, styles['formale'])
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

# ── Prompt formatters per AI ──────────────────────────────────────────────────
def format_chatgpt(vars):
    return f"""# RUOLO
Sei un {vars['RUOLO']}

# CONTESTO
{vars['CONTESTO']}

# COMPITO
{vars['COMPITO']}

# STILE E VINCOLI
{vars['TONO_PROTETTO']}

# OUTPUT ATTESO
- Lingua: Italiano
- Formato: strutturato con sezioni chiare
- Qualità: completo, pronto all'uso, zero editing necessario
- Vincolo critico: Non iniziare mai con "Certamente!", "Certo!" o frasi di conferma vuote. Inizia direttamente con il contenuto richiesto."""

def format_claude(vars):
    return f"""<system>
Sei un {vars['RUOLO']}
</system>

<context>
{vars['CONTESTO']}
</context>

<instructions>
{vars['COMPITO']}
</instructions>

<style>
{vars['TONO_PROTETTO']}
</style>

<output_format>
<language>Italiano</language>
<structure>Usa intestazioni chiare e gerarchia visiva</structure>
<quality>Output immediatamente utilizzabile, nessuna revisione necessaria</quality>
<constraint>Non includere prefazioni, disclaimer o frasi di conferma. Inizia direttamente con il contenuto.</constraint>
</output_format>

<thinking>
Prima di rispondere, analizza: (1) Qual è l'obiettivo reale? (2) Quali sono i vincoli impliciti? (3) Qual è il formato ottimale?
</thinking>"""

def format_gemini(vars):
    return f"""## Profilo esperto
**Ruolo:** {vars['RUOLO']}

## Contesto operativo
{vars['CONTESTO']}

## Obiettivo e metodologia
{vars['COMPITO']}

## Specifiche e Stile
{vars['TONO_PROTETTO']}
| Parametro | Valore |
|-----------|--------|
| Lingua | Italiano |
| Struttura | Sezioni con titoli chiari |
| Qualità | Pronto all'uso |

> Utilizza le tue capacità multimodali e di ricerca aggiornata dove rilevante."""

def format_deepseek(vars):
    return f"""<|System|>
Sei un {vars['RUOLO']}

ATTIVA CHAIN-OF-THOUGHT DETTAGLIATA:
[STEP 1 - COMPRENSIONE] Analizza la richiesta: obiettivo primario, vincoli impliciti, possibili ambiguità.
[STEP 2 - PIANIFICAZIONE] Scomponi il task. Identifica l'approccio ottimale.
[STEP 3 - VALIDAZIONE] Verifica che il piano risponda completamente alla richiesta.
[STEP 4 - ESECUZIONE] Produci l'output seguendo il piano validato.
<|end_of_sentence|>

<|User|>
CONTESTO: {vars['CONTESTO']}

COMPITO:
{vars['COMPITO']}

STILE RICHIESTO:
{vars['TONO_PROTETTO']}
<|end_of_sentence|>

<|Assistant|>"""

def format_llama(vars):
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Sei un {vars['RUOLO']}<|eot_id|>
<|start_header_id|>user<|end_header_id|>

CONTESTO:
{vars['CONTESTO']}

COMPITO E METODOLOGIA:
{vars['COMPITO']}

VINCOLI DI STILE:
{vars['TONO_PROTETTO']}

REQUISITI OUTPUT:
- Risposta in italiano
- Struttura chiara con sezioni
- Output completo e immediatamente utilizzabile<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>"""

def format_perplexity(vars):
    return f"""SEARCH & SYNTHESIZE MODE

Esperto: {vars['RUOLO']}

CONTESTO:
{vars['CONTESTO']}

COMPITO:
{vars['COMPITO']}

STILE:
{vars['TONO_PROTETTO']}

ISTRUZIONI SPECIALI PERPLEXITY:
- Usa le tue capacità di ricerca web in tempo reale per arricchire la risposta con dati aggiornati
- Cita le fonti per ogni affermazione verificabile
- Distingui chiaramente tra informazioni verificate e inferenze
- Prioritizza dati aggiornati rispetto alle conoscenze statiche
- Lingua di risposta: Italiano"""

def format_mistral(vars):
    return f"""[INST] Sei un {vars['RUOLO']}

CONTESTO: {vars['CONTESTO']}

COMPITO:
{vars['COMPITO']}

STILE:
{vars['TONO_PROTETTO']}

REQUISITI:
- Risposta in italiano
- Output strutturato e completo
- Diretto e senza preamboli [/INST]"""

def format_grok(vars):
    return f"""SYSTEM: Sei un {vars['RUOLO']} con accesso a informazioni in tempo reale.

CONTESTO:
{vars['CONTESTO']}

COMPITO:
{vars['COMPITO']}

STILE:
{vars['TONO_PROTETTO']}

SPECIFICHE GROK:
- Sfrutta la tua conoscenza real-time per integrare trend, notizie recenti o dati aggiornati dove rilevante
- Sii diretto, incisivo, e aggiungi una prospettiva non convenzionale se appropriato
- Risposta in italiano, strutturata e immediatamente utilizzabile"""

def format_qwen(vars):
    return f"""<|im_start|>system
Sei un {vars['RUOLO']}

Linee guida:
- Rispondi sempre in italiano
- Struttura la risposta in modo chiaro e gerarchico
- Zero preamboli o disclaimer non necessari
<|im_end|>
<|im_start|>user
CONTESTO: {vars['CONTESTO']}

COMPITO:
{vars['COMPITO']}

STILE:
{vars['TONO_PROTETTO']}
<|im_end|>
<|im_start|>assistant
"""

def format_cohere(vars):
    return f"""## PREAMBLE
Sei un {vars['RUOLO']}

## CONTESTO
{vars['CONTESTO']}

## TASK
{vars['COMPITO']}

## STYLE
{vars['TONO_PROTETTO']}

## OUTPUT REQUIREMENTS
- **Lingua:** Italiano
- **Grounding:** Basa ogni affermazione su evidenze o ragionamenti espliciti
- **Struttura:** Usa markdown con titoli, liste e tabelle dove aumentano la chiarezza
- **RAG mode:** Se disponi di documenti di contesto, prioritizzali rispetto alla conoscenza parametrica"""

def format_gemma(vars):
    return f"""<start_of_turn>user
Ruolo: {vars['RUOLO']}

Contesto: {vars['CONTESTO']}

Task:
{vars['COMPITO']}

Stile e Vincoli:
{vars['TONO_PROTETTO']}

Note:
- Rispondi in italiano
- Struttura l'output con sezioni chiare
- Sii completo e immediatamente utilizzabile
- Non includere preamboli<end_of_turn>
<start_of_turn>model
"""

FORMATTERS = {
    'chatgpt':    format_chatgpt,
    'claude':     format_claude,
    'gemini':     format_gemini,
    'deepseek':   format_deepseek,
    'llama':      format_llama,
    'perplexity': format_perplexity,
    'mistral':    format_mistral,
    'grok':       format_grok,
    'qwen':       format_qwen,
    'cohere':     format_cohere,
    'gemma':      format_gemma,
}

# ── Main build ────────────────────────────────────────────────────────────────
def build_prompt(user_text, ai, tone):
    if ai == 'midjourney':
        return build_midjourney(user_text, tone)
    
    topic = detect_topic(user_text, ai)
    
    prompt_vars = {
        'RUOLO': build_role_string(topic, user_text),
        'CONTESTO': build_protected_context(user_text, topic, ai),
        'COMPITO': build_caged_task(user_text, topic, ai),
        'TONO_PROTETTO': build_protected_tone(tone, ai)
    }
    
    formatter = FORMATTERS.get(ai, format_chatgpt)
    return formatter(prompt_vars)
'''

    # We need to replace everything from `def build_role(` to the end of `def build_prompt(`
    start_str = "def build_role(topic, user_text):"
    end_str = "def build_prompt(user_text, ai, tone):"
    
    start_idx = content.find(start_str)
    
    # find the end of build_prompt
    build_prompt_str = "def build_prompt("
    bp_idx = content.find(build_prompt_str)
    
    # Find next function after build_prompt to know where to end
    next_func_str = "# ── Session history ───────────────────────────────────────────────────────────"
    end_idx = content.find(next_func_str)
    
    if start_idx != -1 and end_idx != -1:
        new_content = content[:start_idx] + new_block + "\\n\\n" + content[end_idx:]
        with open("C:/Users/mendi/Desktop/pe/promptengine.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Success!")
    else:
        print("Error finding boundaries")

if __name__ == '__main__':
    refactor()
