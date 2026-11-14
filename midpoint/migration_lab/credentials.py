"""Explicit local key loading; no shell evaluation and no credential logging."""
import getpass
import os
from pathlib import Path
from .storage import ROOT


PROVIDERS = {'openai': ('OPENAI_API_KEY', '.env'),
             'gemini': ('GEMINI_API_KEY', '.env.gemini')}


def validate_key(key, provider):
    if (not key or any(c.isspace() for c in key) or
            not all(c.isalnum() or c in '._-' for c in key) or
            (provider == 'openai' and not key.startswith('sk-'))):
        raise ValueError('Expected a single API key, without shell syntax')
    return key


def load_key(path=None, *, prompt=False, provider='openai'):
    variable, filename = PROVIDERS[provider]
    if os.environ.get(variable):
        return
    path = Path(path) if path else ROOT / filename
    if path.exists():
        text = path.read_text().strip()
        if text.startswith(variable + '='):
            text = text.split('=', 1)[1].strip()
        os.environ[variable] = validate_key(text, provider)
    elif prompt:
        os.environ[variable] = validate_key(getpass.getpass(f'{provider} API key (hidden, memory only): ').strip(), provider)
    else:
        raise ValueError(f'Configure {variable} or run scripts/configure_key.py --provider {provider}')
