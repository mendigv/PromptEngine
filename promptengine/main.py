#!/usr/bin/env python3
"""
PromptEngine CLI v2.5 - Modular
======================
Secure client: In-process execution, SQLite embedded auth, streaming support.
"""

import sys
import time
from typing import Optional, Tuple

# Import from internal modules
from promptengine.ui.ansi_colors import C
from promptengine.ui.screens import (
    clear, print_logo, safe_input, safe_password_input,
    check_password_strength, choose_ai_ui, choose_tone_ui, get_user_text_ui,
    print_result, show_history_ui, show_2fa_ui,
    stream_llm_response_ui, show_missing_key_banner_ui, show_quality_score_ui
)

from promptengine.auth.local_auth import (
    login_user, register_user, verify_totp_and_activate,
    load_history, save_history, wipe_database
)
from promptengine.auth.key_manager import run_setup_wizard, ensure_key_available, wipe_all_keys
from promptengine.session import current_session
from promptengine.core.router import build_prompt, detect_topic, detect_domain
from promptengine.utils.clipboard import (
    copy_to_clipboard, clipboard_fallback_save, save_to_file
)
from promptengine.engine import call_llm_stream, score_prompt_quality, get_provider_status, MODEL_ROUTING


# ── Authentication Flows ──────────────────────────────────────────────────────

def is_valid_email(email: str) -> bool:
    import re
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

def register_user_flow() -> Tuple[Optional[str], Optional[str]]:
    """Orchestrates registration combining UI and local auth."""
    print(f'\n{C.BOLD}{C.WHITE}--- New User Registration ---{C.RESET}')

    # Local validation
    while True:
        email = safe_input(f'{C.BLUE}▸{C.RESET} Email: ').strip().lower()
        if not is_valid_email(email):
            print(f'  {C.RED}Error: Invalid email format.{C.RESET}')
            continue
        break

    password = safe_password_input(f'{C.BLUE}▸{C.RESET} Password: ', show_strength=True)
    strength, _ = check_password_strength(password)
    if strength == 'WEAK':
        print(f'  {C.RED}Password is too WEAK. Choose a stronger one.{C.RESET}')
        return None, None

    success, err_msg, totp_secret = register_user(email, password)
    if not success:
        print(f'\n  {C.RED}✗ {err_msg}{C.RESET}')
        return None, None

    print(f'\n  {C.GREEN}✓ Account created. Configuring 2FA...{C.RESET}')

    # Step 2: 2FA UI
    show_2fa_ui(email, totp_secret)

    # Step 3: Verify TOTP
    while True:
        token = safe_input(f'{C.BLUE}▸{C.RESET} 6-digit code: ').strip()
        v_success, v_err = verify_totp_and_activate(email, token)
        if v_success:
            print(f'  {C.GREEN}✓ 2FA activated successfully!{C.RESET}')
            print(f'\n  {C.GREEN}✓ Registration complete! Logging in...{C.RESET}')
            return email, "local_token"
        else:
            print(f'  {C.RED}✗ {v_err}{C.RESET}')
            return None, None

def login_user_flow() -> Tuple[Optional[str], Optional[str]]:
    """Orchestrates login combining UI and local auth."""
    print(f'\n{C.BOLD}{C.WHITE}--- System Login ---{C.RESET}')
    email    = safe_input(f'{C.BLUE}▸{C.RESET} Email: ').strip().lower()
    password = safe_password_input(f'{C.BLUE}▸{C.RESET} Password: ', show_strength=False)
    token    = safe_input(f'{C.BLUE}▸{C.RESET} 2FA Code (6 digits): ').strip()

    print(f'  {C.GRAY}Authenticating...{C.RESET}', end='', flush=True)
    success, err_msg = login_user(email, password, token)
    
    if success:
        print(f'\r  {C.GREEN}✓ Login successful.{C.RESET}          ')
        return email, "local_token"
    else:
        print(f'\r  {C.RED}✗ {err_msg}{C.RESET}          ')
        return None, None

def auth_menu_flow() -> None:
    """Handles the initial authentication loop."""
    session = current_session.load()
    if session.is_authenticated:
        current_session.email = session.email
        current_session.token = session.token
        print(f'\n  {C.GREEN}✓ Automatic login: {session.email}{C.RESET}')
        time.sleep(1)
        return

    import os
    if not os.path.exists(os.path.expanduser('~/.promptengine/data.db')):
        clear()
        print_logo()
        run_setup_wizard()
        print(f"\n  {C.GRAY}Please register your first local account.{C.RESET}")
        time.sleep(1)

    while True:
        clear()
        print_logo()
        print(f'{C.BOLD}{C.WHITE}Authentication Required{C.RESET}\n')
        print(f'  {C.GRAY}[1]{C.RESET} {C.YELLOW}Login{C.RESET}')
        print(f'  {C.GRAY}[2]{C.RESET} {C.CYAN}Register{C.RESET}')
        print(f'  {C.GRAY}[3]{C.RESET} {C.RED}Exit{C.RESET}\n')

        choice = safe_input(f'{C.BLUE}▸{C.RESET} Choice [1-3]: ').strip()
        if choice == '1':
            user, token = login_user_flow()
            if user and token:
                current_session.email = user
                current_session.token = token
                current_session.save()
                time.sleep(1.5)
                return
            else:
                safe_input(f'\n  {C.GRAY}Press ENTER to continue...{C.RESET}')
        elif choice == '2':
            user, token = register_user_flow()
            if user and token:
                current_session.email = user
                current_session.token = token
                current_session.save()
                time.sleep(1.5)
                return
            else:
                safe_input(f'\n  {C.GRAY}Press ENTER to continue...{C.RESET}')
        elif choice == '3':
            print(f'\n  {C.GRAY}Exiting. See you!{C.RESET}\n')
            sys.exit(0)
        else:
            print(f'  {C.RED}Invalid option.{C.RESET}')
            time.sleep(1)

# ── Main Loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env for API keys
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print(f'\n{C.BOLD}PromptEngine CLI v2.5{C.RESET} - Professional Prompt Generator')
        print(f'\n{C.GRAY}Single-process — no separate server required.{C.RESET}')
        print(f'\n{C.BOLD}Usage:{C.RESET} python -m promptengine')
        sys.exit(0)

    auth_menu_flow()

    if len(sys.argv) > 1 and sys.argv[1] == '--history':
        hist = load_history(current_session.email)
        show_history_ui(hist)
        sys.exit(0)

    clear()
    print_logo()

    while True:
        # 1. Choose AI
        ai_info = choose_ai_ui()
        if ai_info.get('key') == 'logout':
            current_session.clear()
            print(f'\n  {C.YELLOW}Logged out successfully.{C.RESET}')
            time.sleep(1)
            auth_menu_flow()
            clear()
            print_logo()
            continue

        if ai_info.get('key') == 'wipe':
            print(f'\n  {C.RED}Wiping all data...{C.RESET}')
            wipe_all_keys()
            wipe_database()
            current_session.clear()
            print(f'\n  {C.GREEN}All saved data, API keys, and session databases have been completely wiped.{C.RESET}')
            time.sleep(2)
            clear()
            print_logo()
            auth_menu_flow()
            continue

        # 2. Choose tone
        tone_info = choose_tone_ui()

        # 3. User text
        user_text = get_user_text_ui()
        if not user_text.strip():
            print(f'{C.RED}  No text entered. Try again.{C.RESET}')
            continue

        # 4. Generate
        print(f'\n  {C.VIOLET}Generating...{C.RESET}')

        result = build_prompt(user_text, ai_info['key'], tone_info['key'])

        # 5. Save to history
        save_history(current_session.email, ai_info['name'], tone_info['name'], user_text)

        # 6. Show result
        topic = detect_topic(user_text, ai_info['key'])
        domain_name, domain_role = detect_domain(user_text)
        print_result(result, ai_info, tone_info, user_text, topic, domain_role)

        # 6.5. Direct LLM Execution (Streaming)
        quality = score_prompt_quality(result)
        show_quality_score_ui(quality)
        
        # BYOK Flow: Ensure key is available BEFORE streaming
        req_provider, actual_model = MODEL_ROUTING.get(ai_info['key'], ('groq', 'llama-3.1-8b-instant'))
        obtained_key = ensure_key_available(req_provider)
        
        if obtained_key:
            print(f'\n  {C.VIOLET}Querying LLM...{C.RESET}')
            messages = [{'role': 'user', 'content': result}]
            token_gen = call_llm_stream(ai_key=ai_info['key'], messages=messages)
            
            if token_gen:
                assistant_text = stream_llm_response_ui(token_gen, provider=req_provider, model=actual_model)
                messages.append({'role': 'assistant', 'content': assistant_text})
                
                # Continuous Loop
                while True:
                    print()
                    try:
                        follow_up = input(f"  {C.BLUE}▸{C.RESET} Ask follow-up / new prompt (or type 'exit' to quit): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        follow_up = 'exit'
                    
                    if follow_up.lower() in ('exit', 'quit', 'q'):
                        break
                    if not follow_up:
                        continue
                    
                    messages.append({'role': 'user', 'content': follow_up})
                    print(f'\n  {C.VIOLET}Querying LLM...{C.RESET}')
                    token_gen_followup = call_llm_stream(ai_key=ai_info['key'], messages=messages)
                    if token_gen_followup:
                        assistant_followup = stream_llm_response_ui(token_gen_followup, provider=req_provider, model=actual_model)
                        messages.append({'role': 'assistant', 'content': assistant_followup})
            else:
                show_missing_key_banner_ui(req_provider, actual_model)
        else:
            show_missing_key_banner_ui(req_provider, actual_model)
        
        clear()
        print_logo()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\n\n  {C.GRAY}Exiting. See you!{C.RESET}\n')
        sys.exit(0)
