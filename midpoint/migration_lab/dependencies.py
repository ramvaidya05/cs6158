"""Static import proposals for the current standard-library-only candidate image.

No model-selected package is installed. External imports require a separately
reviewed image lock shared by both runtimes; no guessed PyPI name mappings.
"""
import ast
import sys
from .storage import save_json


def inspect_dependencies(source):
    imports, dynamic = set(), []
    try:
        tree = ast.parse(source, filename='candidate.py')
    except SyntaxError as exc:
        return {'status': 'syntax_error', 'detail': str(exc), 'requirements': [], 'unresolved_imports': []}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.add('<relative-import>')  # Single-module contract has no sibling modules.
            elif node.module:
                imports.add(node.module.split('.')[0])
        elif isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id in ('__import__', 'eval', 'exec'))
                or isinstance(node.func, ast.Attribute) and node.func.attr in ('import_module', 'exec_module')):
            dynamic.append(node.lineno)
    unresolved = sorted(imports - sys.stdlib_module_names - {'__future__'})
    return {'status': 'blocked' if unresolved or dynamic else 'approved',
            'stdlib_imports': sorted(imports - set(unresolved)), 'unresolved_imports': unresolved,
            'dynamic_loading_lines': dynamic, 'requirements': [],
            'policy': 'Single Python module, standard-library only. No third-party distributions approved. '
                      'Static inspection is not a security sandbox or a runtime compatibility guarantee.'}


def write_requirements(candidate, directory):
    result = inspect_dependencies(candidate.read_text(encoding='utf-8'))
    save_json(directory / 'dependencies.json', result)
    # Never emit guessed distributions, URL requirements, or executable pip options.
    (directory / 'requirements.txt').write_text('# No approved third-party dependencies. See dependencies.json for unresolved imports.\n', encoding='utf-8')
    return result
