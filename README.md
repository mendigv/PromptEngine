# PromptEngine 2.0 🚀

**PromptEngine** è un avanzato strumento da riga di comando (CLI) per l'ottimizzazione e la generazione di prompt strutturati per i principali LLM (ChatGPT, Claude, Gemini, DeepSeek, e modelli open-source).

Questo progetto nasce per automatizzare e migliorare la qualità delle interazioni con l'intelligenza artificiale, offrendo prompt completi, contestualizzati e pronti all'uso, il tutto in un ambiente **sicuro, locale e offline-first**.

---

## 🌟 Caratteristiche Principali (Portfolio Highlights)

- **Architettura Locale (In-Process):** Il motore di generazione e l'autenticazione girano interamente in locale usando SQLite, garantendo privacy totale.
- **Machine Learning (TF-IDF) Integrato:** Rilevamento automatico del dominio semantico (tech, salute, storia, ecc.) dell'input utente analizzando il testo in tempo reale tramite `scikit-learn` senza fare chiamate esterne.
- **Supporto BYOK (Bring Your Own Key):** L'utente ha il pieno controllo. Utilizza le proprie chiavi API per interagire direttamente con i provider, evitando server man-in-the-middle.
- **Streaming in Tempo Reale:** Connessione diretta con i provider (Anthropic, OpenAI, Groq) per streamare le risposte direttamente nel terminale.
- **Gestione Sicura dei Segreti:** Flusso di autenticazione protetto tramite hashing PBKDF2 e autenticazione a due fattori (2FA/TOTP) completamente local-first.

---

## 🛠️ Installazione

PromptEngine è stato pacchettizzato per essere installato facilmente su qualsiasi sistema.

1. **Clona il repository:**
   ```bash
   git clone https://github.com/tuo-username/promptengine.git
   cd promptengine
   ```

2. **Crea e attiva un ambiente virtuale (consigliato):**
   ```bash
   python -m venv venv
   # Su Windows:
   venv\Scripts\activate
   # Su macOS/Linux:
   source venv/bin/activate
   ```

3. **Installa le dipendenze:**
   ```bash
   pip install -e .
   ```

---

## ⚙️ Configurazione Iniziale (BYOK)

Per ragioni di sicurezza, PromptEngine si appoggia alle API Key configurate localmente.

1. Rinomina il file `.env.example` in `.env`:
   ```bash
   # Windows
   copy .env.example .env
   # macOS/Linux
   cp .env.example .env
   ```

2. Apri il file `.env` e inserisci le tue chiavi API (es. `OPENAI_API_KEY`, `GROQ_API_KEY`). Solo le chiavi dei modelli che desideri utilizzare sono strettamente necessarie.

---

## 🚀 Utilizzo

Avviare PromptEngine è facilissimo:

```bash
python -m promptengine
```

**Primo accesso:** 
Al primo avvio, il sistema configurerà automaticamente il database SQLite locale `~/.promptengine/data.db` e ti guiderà nella registrazione del tuo account locale (incluso un mock 2FA per testare il livello di sicurezza architetturale).

**Flusso di lavoro:**
1. Fai Login
2. Scegli il modello AI di destinazione (es. Claude 3.5 Sonnet)
3. Scegli il Tono (es. Professionale, Creativo)
4. Inserisci una frase o un'idea grezza.
5. Il motore applicherà il *Quality Score* e genererà il prompt ottimizzato, per poi interrogare (se configurato) il modello in streaming!

---

## 🏗️ Architettura Tecnica

- **Linguaggio:** Python 3.10+
- **Database:** SQLite (Modulo integrato standard)
- **Crittografia & Auth:** `pyotp` (TOTP), `hashlib` (PBKDF2-SHA256)
- **AI Routing & ML:** `requests`, `scikit-learn` (TF-IDF vectorizer)

---
*Creato con passione da [Il Tuo Nome/Username]*
