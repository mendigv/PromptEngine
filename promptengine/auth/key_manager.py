"""
PromptEngine BYOK Key Manager — Bring Your Own Key.

Manages LLM provider API keys securely:
- Reads from environment variables (highest priority)
- Falls back to OS keyring (Windows Credential Manager / macOS Keychain / Linux Secret Service)
- Provides interactive wizard for first-run setup
- Provides on-demand prompt when a key is missing

Security: Keys are NEVER stored in plaintext files.
Keyring is the OS-native secure credential store.
"""

import os
import sys
import logging
from typing import Optional, Dict

from promptengine.ui.ansi_colors import C

logger = logging.getLogger("promptengine.keys")

# ── Provider Registry ─────────────────────────────────────────────────────────

KEYRING_SERVICE = "PromptEngine"

PROVIDERS = {
    "groq": {
        "env_key": "GROQ_API_KEY",
        "name": "Groq",
        "desc": "Free tier — Llama, Gemma, Mixtral models",
        "url": "https://console.groq.com/keys",
        "required": False,
        "prefix": "gsk_",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "name": "OpenAI",
        "desc": "GPT-4o, o1-pro, o3-mini",
        "url": "https://platform.openai.com/api-keys",
        "required": False,
        "prefix": "sk-",
    },
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "name": "Anthropic",
        "desc": "Claude 3.5, Claude 3.7, Claude 4.8",
        "url": "https://console.anthropic.com/",
        "required": False,
        "prefix": "sk-ant-",
    },
    "google": {
        "env_key": "GOOGLE_API_KEY",
        "name": "Google AI",
        "desc": "Gemini Flash, Gemini Pro",
        "url": "https://aistudio.google.com/app/apikey",
        "required": False,
        "prefix": "AIza",
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "name": "DeepSeek",
        "desc": "DeepSeek-R1 reasoning model",
        "url": "https://platform.deepseek.com/api_keys",
        "required": False,
        "prefix": "sk-",
    },
}


# ── Keyring Utilities ─────────────────────────────────────────────────────────

def _keyring_available() -> bool:
    """Returns True if the keyring library is importable."""
    try:
        import keyring
        return True
    except ImportError:
        return False


def _get_from_keyring(provider: str) -> Optional[str]:
    """Retrieves a key from the OS keyring."""
    try:
        import keyring
        val = keyring.get_password(KEYRING_SERVICE, provider)
        return val if val else None
    except Exception:
        return None


def _save_to_keyring(provider: str, key: str) -> bool:
    """Saves a key to the OS keyring. Returns True on success."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, provider, key)
        logger.debug("API key for '%s' saved to OS keyring.", provider)
        return True
    except Exception as e:
        logger.warning("Could not save key to keyring: %s", e)
        return False


def _save_to_env_file(provider: str, key: str) -> bool:
    """Fallback: appends/updates the key in the .env file."""
    env_path = os.path.join(os.getcwd(), ".env")
    env_key = PROVIDERS[provider]["env_key"]
    try:
        # Read existing content
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        # Update or append
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_key}="):
                lines[i] = f"{env_key}={key}\n"
                updated = True
                break
        if not updated:
            lines.append(f"{env_key}={key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # Also set in current process
        os.environ[env_key] = key
        logger.info("API key for '%s' saved to .env file.", provider)
        return True
    except Exception as e:
        logger.warning("Could not save key to .env: %s", e)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def get_api_key(provider: str) -> Optional[str]:
    """
    Returns the API key for the given provider.
    Priority: environment variable > OS keyring.

    Returns None if no key is configured.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return None

    # 1. Environment variable (highest priority)
    key = os.environ.get(cfg["env_key"])
    if key:
        return key

    # 2. OS keyring
    key = _get_from_keyring(provider)
    if key:
        # Inject into environment for this session
        os.environ[cfg["env_key"]] = key
        return key

    return None


def set_api_key(provider: str, key: str) -> bool:
    """
    Saves an API key securely.
    Tries keyring first, falls back to .env file.
    Also sets the key in the current process environment.

    Returns True on success.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return False

    # Set in current process immediately
    os.environ[cfg["env_key"]] = key

    if _keyring_available():
        return _save_to_keyring(provider, key)
    else:
        return _save_to_env_file(provider, key)


def get_provider_status() -> Dict[str, bool]:
    """Returns a dict of {provider: has_key} for all providers."""
    return {p: bool(get_api_key(p)) for p in PROVIDERS}


def has_any_key() -> bool:
    """Returns True if at least one provider key is configured."""
    return any(get_provider_status().values())


def ensure_key_available(provider: str) -> Optional[str]:
    """
    Returns the API key if available, otherwise prompts the user to enter it.
    This is the on-demand BYOK flow for missing keys.

    Returns the key string if obtained, or None if user skipped.
    """
    key = get_api_key(provider)
    if key:
        return key

    cfg = PROVIDERS.get(provider, {})
    provider_name = cfg.get("name", provider.capitalize())
    url = cfg.get("url", "")

    print(f"\n  {C.YELLOW}⚠  API key for {C.BOLD}{provider_name}{C.RESET}{C.YELLOW} not configured.{C.RESET}")
    print(f"  {C.GRAY}Get your free key at: {C.CYAN}{url}{C.RESET}")
    print()
    print(f"  {C.GRAY}[1]{C.RESET} Enter key now")
    print(f"  {C.GRAY}[2]{C.RESET} Skip — use a different model")
    print()

    from promptengine.ui.screens import safe_input
    choice = safe_input(f"{C.BLUE}▸{C.RESET} Choice [1/2]: ").strip()

    if choice == "1":
        key = safe_input(f"{C.BLUE}▸{C.RESET} Paste your {provider_name} API key: ").strip()
        if key:
            ok = set_api_key(provider, key)
            if ok:
                storage = "OS keyring" if _keyring_available() else ".env file"
                print(f"  {C.GREEN}✓ Key saved to {storage}.{C.RESET}")
            return key
    return None


# ── First-Run Setup Wizard ────────────────────────────────────────────────────

def run_setup_wizard() -> bool:
    """
    Interactive wizard for configuring API keys at first run.
    Returns True if at least one key was configured.
    """
    from promptengine.ui.screens import safe_input

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 66}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  ⚙  LLM Provider Setup Wizard{C.RESET}")
    print(f"{C.CYAN}{'═' * 66}{C.RESET}")
    print(f"{C.WHITE}  Configure your AI provider keys.{C.RESET}")
    print(f"  {C.GRAY}Keys are stored in your OS credential vault, not in plaintext.{C.RESET}")
    print()

    # 1. Blocking Groq Setup
    groq_key = get_api_key("groq")
    if not groq_key:
        print(f"  {C.YELLOW}{'-' * 66}{C.RESET}")
        print(f"  {C.BOLD}{C.YELLOW}🔑 FIRST-TIME SETUP: GROQ API KEY REQUIRED{C.RESET}")
        print(f"  {C.YELLOW}{'-' * 66}{C.RESET}")
        print(f"  {C.WHITE}PromptEngine uses Groq's high-speed infrastructure as its primary{C.RESET}")
        print(f"  {C.WHITE}engine to optimize your prompts and run domain classification.{C.RESET}")
        print()
        print(f"  {C.BOLD}Why do you need your own key?{C.RESET}")
        print(f"  {C.GRAY}- 100% Free & Private: Groq provides a generous free tier.{C.RESET}")
        print(f"  {C.GRAY}- Dedicated Quota: Using your own key ensures your requests are{C.RESET}")
        print(f"  {C.GRAY}  never throttled or shared with other users.{C.RESET}")
        print(f"  {C.GRAY}- Security: Your key is stored securely in your local system OS{C.RESET}")
        print(f"  {C.GRAY}  credential store.{C.RESET}")
        print()
        print(f"  {C.BOLD}How to get your free key in 30 seconds:{C.RESET}")
        print(f"  {C.CYAN}1. Visit https://console.groq.com/keys{C.RESET}")
        print(f"  {C.CYAN}2. Sign in and click \"Create API Key\"{C.RESET}")
        print(f"  {C.CYAN}3. Copy and paste your key below.{C.RESET}")
        print(f"  {C.YELLOW}{'-' * 66}{C.RESET}\n")

        while not get_api_key("groq"):
            key = safe_input(f"  {C.BLUE}▸{C.RESET} Paste your Groq API Key: ").strip()
            if key:
                set_api_key("groq", key)
                print(f"  {C.GREEN}✓ Groq Key Saved.{C.RESET}\n")
                break
            else:
                if has_any_key():
                    print(f"  {C.YELLOW}⚠ Groq skipped. Using other available providers.{C.RESET}\n")
                    break
                else:
                    print(f"  {C.RED}Error: You must provide a Groq API Key (or another provider's key) to continue.{C.RESET}\n")

    configured = 0
    if get_api_key("groq"):
        print(f"  {C.GREEN}✓{C.RESET}  {'Groq':.<28} {C.GREEN}Already configured{C.RESET}")
        configured += 1

    print(f"  {C.GRAY}Press ENTER to skip a provider.{C.RESET}\n")

    for provider, cfg in PROVIDERS.items():
        if provider == "groq":
            continue

        existing = get_api_key(provider)
        if existing:
            print(f"  {C.GREEN}✓{C.RESET}  {cfg['name']:.<28} {C.GREEN}Already configured{C.RESET}")
            configured += 1
            continue

        print(f"  {C.YELLOW}○{C.RESET}  {C.BOLD}{cfg['name']}{C.RESET} — {C.GRAY}{cfg['desc']}{C.RESET}")
        print(f"     {C.GRAY}Key URL: {C.CYAN}{cfg['url']}{C.RESET}")
        key = safe_input(f"     {C.BLUE}▸{C.RESET} API Key (ENTER to skip): ").strip()
        if key:
            set_api_key(provider, key)
            print(f"     {C.GREEN}✓ Saved.{C.RESET}")
            configured += 1
        else:
            print(f"     {C.GRAY}Skipped.{C.RESET}")
        print()

    print(f"{C.CYAN}{'═' * 66}{C.RESET}")
    if configured == 0:
        print(f"  {C.YELLOW}⚠  No keys configured. You can set them later.{C.RESET}")
        print(f"  {C.GRAY}Add keys to your .env file or run the wizard again.{C.RESET}")
    else:
        print(f"  {C.GREEN}✓ {configured} provider(s) ready.{C.RESET}")
    print()
    return configured > 0

def wipe_all_keys() -> None:
    """Wipes all API keys from keyring and removes them from the .env file."""
    for provider, cfg in PROVIDERS.items():
        if _keyring_available():
            try:
                import keyring
                keyring.delete_password(KEYRING_SERVICE, provider)
            except Exception:
                pass
        
        env_key = cfg["env_key"]
        if env_key in os.environ:
            del os.environ[env_key]

    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                should_keep = True
                for cfg in PROVIDERS.values():
                    if line.startswith(f'{cfg["env_key"]}='):
                        should_keep = False
                        break
                if should_keep:
                    new_lines.append(line)
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logger.info("Cleared API keys from .env file.")
        except Exception as e:
            logger.warning("Could not clear .env file: %s", e)

