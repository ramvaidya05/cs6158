"""Save an API key in the ignored local .env file, without echo or shell history."""
import getpass
import os
from pathlib import Path


def main():
    path = Path(__file__).resolve().parents[1] / '.env'
    key = getpass.getpass('Paste the NEW OpenAI API key (input is hidden): ').strip()
    if not key.startswith('sk-') or '\n' in key:
        raise SystemExit('Expected one OpenAI API key; no file written')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write('OPENAI_API_KEY=' + key + '\n')
    print('Saved in midpoint/.env with owner-only permissions. The file is ignored by Git.')


if __name__ == '__main__':
    main()
