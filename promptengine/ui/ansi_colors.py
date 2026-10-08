"""Costanti dei colori ANSI e utility testuali."""

import shutil
import textwrap

class C:
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    BLUE    = '\033[38;5;33m'
    VIOLET  = '\033[38;5;135m'
    CYAN    = '\033[38;5;39m'
    GREEN   = '\033[38;5;82m'
    YELLOW  = '\033[38;5;220m'
    RED     = '\033[38;5;196m'
    WHITE   = '\033[97m'
    GRAY    = '\033[38;5;245m'
    BG_DARK = '\033[48;5;234m'

def gradient(text: str) -> str:
    """Applica un gradiente blu→viola carattere per carattere."""
    blues   = [33, 33, 69, 69, 105, 105]
    out = ''
    for i, ch in enumerate(text):
        idx = min(i, len(blues) - 1)
        out += f'\033[38;5;{blues[idx]}m{ch}'
    return out + C.RESET

def box(text: str, color: str = C.VIOLET, width: int | None = None) -> str:
    """Disegna un box con bordi."""
    w = width or min(shutil.get_terminal_size().columns - 4, 80)
    lines = text.split('\n')
    top    = f'{color}╭{"─"*(w)}╮{C.RESET}'
    bottom = f'{color}╰{"─"*(w)}╯{C.RESET}'
    body   = '\n'.join(f'{color}│{C.RESET} {l:<{w-2}} {color}│{C.RESET}' for l in lines)
    return f'{top}\n{body}\n{bottom}'

def header_line(title: str, color: str = C.BLUE) -> str:
    w = min(shutil.get_terminal_size().columns - 2, 80)
    side = (w - len(title) - 2) // 2
    return f'{color}{"─"*side} {C.BOLD}{title}{C.RESET}{color} {"─"*side}{C.RESET}'

def wrap(text: str, width: int = 76, indent: int = 0) -> str:
    """Wrappa testo a width con indentazione."""
    prefix = ' ' * indent
    return '\n'.join(textwrap.fill(p, width, initial_indent=prefix, subsequent_indent=prefix)
                     for p in text.split('\n'))
