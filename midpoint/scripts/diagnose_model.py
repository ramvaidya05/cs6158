"""Small adapter probe; sends no repository data and logs only sanitized errors."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.credentials import load_key
from migration_lab.backends import OpenAIResponsesBackend, BackendError
from migration_lab.budget import SpendBudget
from migration_lab.storage import new_run, save_json
from migration_lab.experiments import archive_run


def main():
    load_key(prompt=True)
    path=new_run('adapter-diagnosis')
    budget=SpendBudget(0.05,4,20,path/'spend.json')
    result={'purpose':'Adapter access diagnosis, not a translation-accuracy trial','model':'gpt-5.6-sol'}
    try:
        response=OpenAIResponsesBackend('gpt-5.6-sol','medium',budget).generate(
            'diagnostic',0,'Return a Python module defining run(*args) that returns 0. Explain in one word.',max_output_tokens=128)
        result.update(status='completed',metadata=response['metadata'])
    except BackendError as exc:
        result.update(status='error',kind=exc.kind,details=exc.details,message=str(exc))
    finally:
        os.environ.pop('OPENAI_API_KEY',None)
        save_json(path/'result.json',result)
        print(result)
        print('Archived:',archive_run(path))
    return 0 if result['status']=='completed' else 1


if __name__=='__main__':
    raise SystemExit(main())
