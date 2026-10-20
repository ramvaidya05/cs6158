"""Explicit local key loading; no shell evaluation and no credential logging."""
import getpass
import os
from pathlib import Path
from .storage import ROOT


def load_key(path=None, *, prompt=False):
    if os.environ.get('OPENAI_API_KEY'):
        return
    path = Path(path) if path else ROOT / '.env'
    if path.exists():
        text = path.read_text().strip()
        if text.startswith('OPENAI_API_KEY='):
            text = text.split('=', 1)[1].strip()
        if '\n' in text or not text.startswith('sk-'):
            raise ValueError('Key file must contain only OPENAI_API_KEY=<key> or the raw key')
        os.environ['OPENAI_API_KEY'] = text
    elif prompt:
        os.environ['OPENAI_API_KEY'] = getpass.getpass('API key (hidden, memory only): ')
    else:
        raise ValueError('Configure OPENAI_API_KEY or run scripts/configure_key.py')
