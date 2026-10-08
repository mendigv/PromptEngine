"""Graphic TTY functions, logos, menus, and safe input."""

import os
import sys
import shutil
import textwrap
from typing import Tuple, Dict, Any, List

from promptengine.ui.ansi_colors import C, header_line
from promptengine.config.models_config import AI_MODELS, TONES

def clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')

def safe_input(prompt_str: str = '') -> str:
    """Wrapper sicuro per input() che gestisce EOFError e KeyboardInterrupt."""
    try:
        return input(prompt_str)
    except EOFError:
        print(f'\n  {C.YELLOW}[EOF] Input ended. Safe exit.{C.RESET}')
        sys.exit(0)
    except KeyboardInterrupt:
        print(f'\n\n  {C.GRAY}Exiting. See you!{C.RESET}\n')
        sys.exit(0)

def pulisci_buffer_input() -> None:
    """Flushes the standard input buffer (cross-platform)."""
    try:
        if sys.platform == 'win32':
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            import select
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
    except Exception:
        pass

def check_password_strength(pw: str) -> Tuple[str, str]:
    if len(pw) < 6 or pw.isalpha():
        return 'WEAK', '\033[91m'

    has_upper   = any(c.isupper() for c in pw)
    has_lower   = any(c.islower() for c in pw)
    has_digit   = any(c.isdigit() for c in pw)
    has_special = any(not c.isalnum() for c in pw)

    if len(pw) >= 10 and has_upper and has_lower and has_digit and has_special:
        return 'STRONG', '\033[92m'

    if len(pw) >= 8 and has_digit and (has_upper or has_lower):
        return 'MEDIUM', '\033[93m'

    return 'WEAK', '\033[91m'

def real_time_password_input(prompt_str: str, show_strength: bool = False) -> str:
    print(prompt_str, end='', flush=True)
    pw = ""

    def render(p: str) -> None:
        if show_strength:
            strength, color = check_password_strength(p) if p else ('', '')
            indicator = f" [{color}{strength}{C.RESET}]" if strength else ""
        else:
            indicator = ""
        line = f"\r{prompt_str}{'*' * len(p)}{indicator}"
        sys.stdout.write(line + " " * 20 + f"\r{line}")
        sys.stdout.flush()

    if sys.platform == 'win32':
        import msvcrt
        while True:
            char = msvcrt.getch()
            if char in (b'\r', b'\n'):
                print()
                return pw
            elif char in (b'\x08', b'\x7f'):  # backspace
                if len(pw) > 0:
                    pw = pw[:-1]
                    render(pw)
            elif char == b'\x03':  # ctrl+c
                raise KeyboardInterrupt
            elif char == b'\x04':  # ctrl+d
                raise EOFError
            else:
                try:
                    c = char.decode('utf-8')
                    pw += c
                    render(pw)
                except UnicodeDecodeError:
                    pass
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            while True:
                char = sys.stdin.read(1)
                if char in ('\r', '\n'):
                    sys.stdout.write('\r\n')
                    return pw
                elif char in ('\x7f', '\b', '\x08'):  # backspace
                    if len(pw) > 0:
                        pw = pw[:-1]
                        render(pw)
                elif char == '\x03':  # ctrl+c
                    raise KeyboardInterrupt
                elif char == '\x04':  # ctrl+d
                    raise EOFError
                else:
                    pw += char
                    render(pw)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def safe_password_input(prompt_str: str, show_strength: bool = False) -> str:
    try:
        return real_time_password_input(prompt_str, show_strength)
    except EOFError:
        print(f'\n  {C.YELLOW}[EOF] Input ended. Safe exit.{C.RESET}')
        sys.exit(0)
    except KeyboardInterrupt:
        print(f'\n\n  {C.GRAY}Exiting. See you!{C.RESET}\n')
        sys.exit(0)

def print_logo() -> None:
    print()
    logo_lines = [
        '██████╗ ██████╗  ██████╗ ███╗   ███╗██████╗ ████████╗',
        '██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝',
        '██████╔╝██████╔╝██║   ██║██╔████╔██║██████╔╝   ██║   ',
        '██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔═══╝    ██║   ',
        '██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║        ██║   ',
        '╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝        ╚═╝   ',
    ]
    colors = [C.BLUE, C.BLUE, C.VIOLET, C.VIOLET, C.VIOLET, C.VIOLET]
    for line, col in zip(logo_lines, colors):
        print(f'  {col}{line}{C.RESET}')
    print(f'  {C.GRAY}ENGINE{C.RESET}')
    print(f'  {C.GRAY}Professional Prompt Optimizer for 12+ AI models{C.RESET}')
    print()

def choose_ai_ui() -> Dict[str, Any]:
    from promptengine.config.config_loader import get_models_with_submodels
    models = get_models_with_submodels()
    
    print(f'\n{C.BOLD}{C.WHITE}Select AI model:{C.RESET}')
    print()
    cols = 2
    items = list(models.items())
    for i in range(0, len(items), cols):
        row = items[i:i+cols]
        line = ''
        for num, info in row:
            line += f'  {C.GRAY}[{num:>2}]{C.RESET} {info["color"]}{info["icon"]} {info["name"]:<28}{C.RESET}'
        print(line)
    print(f'  {C.GRAY}[ 0]{C.RESET} {C.RED}Logout{C.RESET}')
    print(f'  {C.GRAY}[99]{C.RESET} {C.RED}Factory Reset / Wipe All Data{C.RESET}')
    print()
    
    while True:
        max_num = len(models)
        choice = safe_input(f'{C.BLUE}▸{C.RESET} Select a number [1-{max_num}]: ').strip()
        if choice == '0' or choice.lower() in ('logout', 'exit'):
            return {'key': 'logout'}
        if choice == '99':
            return {'key': 'wipe'}
        if choice in models:
            selected = models[choice]
            sub_models = selected.get('sub_models')
            if sub_models:
                print(f'\n{C.BOLD}{C.WHITE}Select version:{C.RESET}')
                for snum, sinfo in sub_models.items():
                    desc = sinfo.get('desc', '')
                    print(f'  {C.GRAY}[{snum}]{C.RESET} {C.YELLOW}{sinfo["name"]}{C.RESET} {C.GRAY}({desc}){C.RESET}')
                while True:
                    sub = safe_input(f'{C.BLUE}▸{C.RESET} Choice [1-{len(sub_models)}]: ').strip()
                    if sub in sub_models:
                        return {
                            'key': sub_models[sub]['key'],
                            'name': sub_models[sub]['name'],
                            'color': selected['color'],
                            'icon': selected['icon']
                        }
                    print(f'{C.RED}  Enter a valid number.{C.RESET}')
            return selected
        print(f'{C.RED}  Enter a valid number.{C.RESET}')

def choose_tone_ui() -> Dict[str, str]:
    print(f'\n{C.BOLD}{C.WHITE}Select tone:{C.RESET}')
    print()
    for num, info in TONES.items():
        print(f'  {C.GRAY}[{num}]{C.RESET} {C.YELLOW}{info["name"]:<12}{C.RESET} {C.GRAY}{info["desc"]}{C.RESET}')
    print()
    while True:
        choice = safe_input(f'{C.BLUE}▸{C.RESET} Choice [1-4]: ').strip()
        if choice in TONES:
            return TONES[choice]
        print(f'{C.RED}  Enter a number between 1 and 4.{C.RESET}')

def get_user_text_ui() -> str:
    """Prompts the user for their raw prompt text. Single ENTER to confirm."""
    print(f'\n{C.BOLD}{C.WHITE}Enter your raw prompt:{C.RESET}')
    print()
    try:
        line = input(f'{C.BLUE}  │{C.RESET} ')
    except (EOFError, KeyboardInterrupt):
        line = ""
    return line

def print_result(prompt_text: str, ai_info: Dict[str, Any], tone_info: Dict[str, str], user_text: str, topic: str, domain_role: str | None) -> None:
    w = min(shutil.get_terminal_size().columns - 4, 84)
    topic_names = {
        'email': 'Professional Email', 'code': 'Code & Development',
        'content': 'Content & Copy', 'summary': 'Summary & Analysis',
        'strategy': 'Strategy & Business', 'translation': 'Translation',
        'explain': 'Explanation', 'image': 'Visual Prompt', 'general': 'General Response',
    }
    wc   = len(user_text.split())
    mult = {'formale': 1.4, 'creativo': 1.2, 'tecnico': 1.8, 'ironico': 1.1}.get(tone_info['key'], 1.2)
    mins = max(3, round(wc * 0.08 * mult))
    time_saved = f'{mins} minutes'

    print()
    print(header_line('OPTIMIZED PROMPT', C.VIOLET))
    print()
    print(f'  {C.GRAY}AI:{C.RESET}        {ai_info["color"]}{ai_info["icon"]} {ai_info["name"]}{C.RESET}')
    print(f'  {C.GRAY}Tone:{C.RESET}      {C.YELLOW}{tone_info["name"]}{C.RESET}')
    print(f'  {C.GRAY}Category:{C.RESET} {C.CYAN}{topic_names.get(topic, "General")}{C.RESET}')
    if domain_role and topic in ('explain', 'general'):
        print(f'  {C.GRAY}Domain:{C.RESET}   {C.CYAN}{domain_role[:60]}...{C.RESET}' if len(domain_role) > 60 else f'  {C.GRAY}Domain:{C.RESET}   {C.CYAN}{domain_role}{C.RESET}')
    print(f'  {C.GRAY}Estimated time saved:{C.RESET} {C.GREEN}{time_saved}{C.RESET}')
    print()
    print(f'  {C.VIOLET}{"─"*(w-2)}{C.RESET}')
    print()

    for line in prompt_text.split('\n'):
        if line.startswith('#') or line.startswith('===') or line.startswith('['):
            print(f'  {C.BOLD}{C.BLUE}{line}{C.RESET}')
        elif line.startswith('<') and line.endswith('>'):
            print(f'  {C.VIOLET}{line}{C.RESET}')
        elif line.startswith('Passo ') or line.startswith('STEP '):
            print(f'  {C.CYAN}{line}{C.RESET}')
        elif line.strip() == '':
            print()
        else:
            wrapped = textwrap.fill(line, w-4, initial_indent='  ', subsequent_indent='  ')
            print(f'{C.WHITE}{wrapped}{C.RESET}')

    print()
    print(f'  {C.VIOLET}{"─"*(w-2)}{C.RESET}')

def show_history_ui(hist: List[Dict[str, Any]]) -> None:
    if not hist:
        print(f'\n  {C.GRAY}No previous sessions found.{C.RESET}\n')
        return
    print(f'\n{C.BOLD}{C.WHITE}Last {min(5, len(hist))} sessions:{C.RESET}\n')
    for i, h in enumerate(hist[:5], 1):
        print(f'  {C.GRAY}[{i}]{C.RESET} {C.CYAN}{h.get("ai","?")} · {h.get("tone","?")}{C.RESET}')
        print(f'       {C.GRAY}{h.get("user_text","")[:70]}...{C.RESET}')
        print()

# Menu rimosso in favore del continuous loop

def show_2fa_ui(email: str, totp_secret: str) -> None:
    print(f'\n{C.CYAN}=================================================={C.RESET}')
    print(f'{C.BOLD}{C.CYAN}🔒 SECURITY SETUP (Google Authenticator){C.RESET}')
    print(f'{C.CYAN}=================================================={C.RESET}')
    print(f'{C.WHITE}To protect your account, we enable two-factor authentication.{C.RESET}\n')
    print(f'{C.GRAY}Step 1:{C.RESET} {C.WHITE}Install the "Google Authenticator" app on your smartphone{C.RESET}')
    print(f'         {C.DIM}(available for free on the App Store or Google Play Store).{C.RESET}\n')
    print(f'{C.GRAY}Step 2:{C.RESET} {C.WHITE}Open the app on your phone and tap the "+" button.{C.RESET}\n')
    print(f'{C.GRAY}Step 3:{C.RESET} {C.WHITE}Select "Enter a setup key" and fill in:{C.RESET}')
    print(f'         {C.BLUE}• Account name:{C.RESET} PromptEngine ({email})')
    print(f'         {C.BLUE}• Secret key:{C.RESET} {C.YELLOW}{totp_secret}{C.RESET}')
    print(f'         {C.BLUE}• Key type:{C.RESET} Time-based (TOTP)\n')
    print(f'{C.GRAY}Step 4:{C.RESET} {C.WHITE}Enter the 6-digit code from your app below to confirm activation.{C.RESET}')
    print(f'{C.CYAN}=================================================={C.RESET}\n')

def show_llm_response_ui(response_text: str) -> None:
    """Shows the AI response with a progressive typing effect."""
    import time as _time
    w = min(shutil.get_terminal_size().columns - 4, 84)
    
    print(f"\n{C.GRAY}{'\u2500' * w}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}  \u2b22 AI Response:{C.RESET}\n")
    
    lines = response_text.split('\n')
    for i, line in enumerate(lines):
        # Syntax highlighting per blocchi di codice
        stripped = line.strip()
        if stripped.startswith('```'):
            styled = f'  {C.CYAN}{line}{C.RESET}'
        elif stripped.startswith('#'):
            styled = f'  {C.BOLD}{C.BLUE}{line}{C.RESET}'
        elif stripped.startswith('- ') or stripped.startswith('* '):
            styled = f'  {C.YELLOW}\u2022{C.RESET} {line.strip()[2:]}'
        elif stripped.startswith('> '):
            styled = f'  {C.VIOLET}\u2502 {line.strip()[2:]}{C.RESET}'
        else:
            # Wrap lunghe righe
            if len(line) > w - 4:
                wrapped = textwrap.fill(line, w - 4)
                styled = f'  {wrapped}'
            else:
                styled = f'  {line}'
        
        if i < 5 and len(styled) < 200:
            for char in styled:
                print(char, end='', flush=True)
                _time.sleep(0.008)
            print()
        else:
            print(styled)
    
    print(f"\n{C.GRAY}{'\u2500' * w}{C.RESET}")

def stream_llm_response_ui(token_generator, provider: str = "", model: str = "") -> str:
    """Streams LLM response tokens to the terminal in real-time.
    
    Args:
        token_generator: A generator yielding text tokens (strings)
        provider: Provider name for the header display
        model: Model name for the header display
    
    Returns:
        The complete response text (concatenated tokens)
    """
    w = min(shutil.get_terminal_size().columns - 4, 84)
    label = f"{provider}/{model}" if provider and model else "AI"
    
    print(f"\n{C.GRAY}{'─' * w}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}  ⬡ Response from {label}:{C.RESET}\n")
    print(f"  ", end='', flush=True)  # Initial indent
    
    full_response = []
    char_count = 0
    
    for token in token_generator:
        full_response.append(token)
        # Handle newlines with proper indentation
        for char in token:
            if char == '\n':
                print(f"\n  ", end='', flush=True)
                char_count = 0
            else:
                print(char, end='', flush=True)
                char_count += 1
    
    print()  # Final newline
    print(f"\n{C.GRAY}{'─' * w}{C.RESET}")
    
    return ''.join(full_response)

def show_missing_key_banner_ui(provider: str, model: str, url: str = "") -> None:
    """Shows a clear banner when an API key is missing for the selected provider."""
    w = min(shutil.get_terminal_size().columns - 4, 84)
    print(f"\n  {C.YELLOW}{'▲' * min(w-4, 60)}{C.RESET}")
    print(f"  {C.BOLD}{C.YELLOW}⚠  Missing API Key for {provider.upper()}{C.RESET}")
    print(f"  {C.WHITE}You selected {model}, which requires a {provider.capitalize()} API key.{C.RESET}")
    if url:
        print(f"  {C.GRAY}Get your key at: {C.CYAN}{url}{C.RESET}")
    print(f"  {C.YELLOW}{'▲' * min(w-4, 60)}{C.RESET}\n")

def show_provider_status_ui(status: dict) -> None:
    """Shows the status of configured LLM providers."""
    print(f'\n  {C.BOLD}{C.WHITE}Configured LLM Providers:{C.RESET}')
    for provider, available in status.items():
        icon = f'{C.GREEN}\u2713{C.RESET}' if available else f'{C.RED}\u2717{C.RESET}'
        print(f'    {icon} {provider.capitalize():.<20} {"API key found" if available else "Not configured"}')
    print()

def show_quality_score_ui(score: dict) -> None:
    """Shows the prompt quality score with a visual bar."""
    overall = score.get('overall', 0)
    # Visual bar
    filled = int(overall)
    bar = f'{C.GREEN}{"\u2588" * filled}{C.GRAY}{"\u2591" * (10 - filled)}{C.RESET}'
    
    color = C.GREEN if overall >= 7 else (C.YELLOW if overall >= 4 else C.RED)
    
    print(f'\n  {C.BOLD}Prompt Quality:{C.RESET} {bar} {color}{overall}/10{C.RESET}')
    print(f'  {C.GRAY}Structure: {score.get("structure", 0):.1f} | '
          f'Specificity: {score.get("specificity", 0):.1f} | '
          f'Constraints: {score.get("constraints", 0):.1f} | '
          f'{score.get("word_count", 0)} words{C.RESET}')
