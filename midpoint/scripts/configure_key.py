"""Save an API key in the ignored local .env file, without echo or shell history."""
import getpass
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.credentials import PROVIDERS, validate_key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=PROVIDERS, default='openai')
    args = parser.parse_args()
    variable, filename = PROVIDERS[args.provider]
    path = ROOT / filename
    key = validate_key(getpass.getpass(f'Paste the {args.provider} API key (input is hidden): ').strip(), args.provider)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(variable + '=' + key + '\n')
    print(f'Saved in midpoint/{filename} with owner-only permissions. The file is ignored by Git.')


if __name__ == '__main__':
    main()
