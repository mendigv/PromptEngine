"""Utility per copia-incolla e salvataggio file locali."""

import os
import sys
import json
import datetime
from typing import List, Dict, Any, Optional
from promptengine.ui.ansi_colors import C

HISTORY_FILE_TEMPLATE = '~/.promptengine_history_{}.json'

def get_history_file(email: Optional[str]) -> str:
    if email:
        return os.path.expanduser(HISTORY_FILE_TEMPLATE.format(email))
    return os.path.expanduser('~/.promptengine_history.json')

def load_history(email: Optional[str]) -> List[Dict[str, Any]]:
    try:
        with open(get_history_file(email), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return []

def save_to_history(email: Optional[str], entry: Dict[str, Any]) -> None:
    hist = load_history(email)
    hist.insert(0, entry)
    hist = hist[:50]
    try:
        with open(get_history_file(email), 'w', encoding='utf-8') as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
    except (OSError, PermissionError):
        pass

def copy_to_clipboard(text: str) -> bool:
    """Copia negli appunti (richiede xclip/xsel su Linux, pbcopy su Mac).
    Restituisce True se la copia è riuscita, False altrimenti."""
    try:
        if sys.platform == 'darwin':
            import subprocess
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p.stdin.write(text.encode())
            p.stdin.close()
            p.wait()
            return True
        elif sys.platform.startswith('linux'):
            import subprocess
            for cmd in ['xclip -selection clipboard', 'xsel --clipboard --input']:
                try:
                    p = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE)
                    p.stdin.write(text.encode())
                    p.stdin.close()
                    p.wait()
                    return True
                except FileNotFoundError:
                    continue
        elif sys.platform == 'win32':
            import subprocess
            p = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
            p.stdin.write(text.encode('utf-16'))
            p.stdin.close()
            p.wait()
            return True
    except Exception:
        pass
    return False

def clipboard_fallback_save(text: str, ai_name: str = 'prompt') -> Optional[str]:
    """Fallback: salva il prompt su file locale quando la clipboard non è disponibile."""
    fallback_path = 'output_prompt.txt'
    try:
        with open(fallback_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return fallback_path
    except (OSError, PermissionError):
        return None

def save_to_file(text: str, ai_name: str, tone_name: str) -> Optional[str]:
    """Salva il prompt su file .txt generato dinamicamente."""
    ts    = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f'prompt_{ai_name.lower().replace(" ", "_")}_{ts}.txt'
    try:
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f'AI: {ai_name}\nTono: {tone_name}\n\n')
            f.write(text)
        return fname
    except (OSError, PermissionError) as e:
        print(f'  {C.RED}Errore nel salvataggio: {e}{C.RESET}')
        return None
