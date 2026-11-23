"""CLI v4 coverage for nullable lookups after parser reuse."""
from .cli_extended import cases as v3, group_setup
from .cli_semantic import setup, parse
from .cli_task import call, contract
from .scenarios import validate_cases


def cases(split, seed=6158):
    rows = v3(split, seed)
    if split == 'visible':
        # Previously inspected holdout is development coverage from v4 onward.
        rows.extend(v3('holdout', seed))
        additions = [
            setup() + [parse([]), call('cmd', 'getOptionValues', '--output')],
            setup() + [parse(['-v']), call('cmd', 'getOptionValue', 'output')],
            setup() + [parse(['-o', 'before']), parse([], save='second'),
                       call('second', 'hasOption', 'output'), call('cmd', 'getOptionValues', 'o')],
        ]
    else:
        # Remove exposed v3 holdout from scoring. Use fresh operation compositions.
        rows = []
        additions = []
        for label, argv, old_alias, new_alias in (
            ('archive', ['--output=archive', '-v'], '--output', '-o'),
            ('folder', ['-o', 'folder'], 'output', '--output'),
            ('index', ['--output', 'index'], '-o', 'output'),
        ):
            for getter in ('hasOption', 'getOptionValue', 'getOptionValues'):
                additions.append(setup() + [parse(argv), parse(['--', label], save='second'),
                    call('second', getter, new_alias), call('second', getter, '--unregistered'),
                    call('cmd', getter, old_alias), call('second', 'getArgs')])
        for getter in ('hasOption', 'getOptionValue', 'getOptionValues'):
            additions.append(group_setup() + [parse(['--xml']), parse(['-j'], save='second'),
                call('second', getter, '--xml'), call('cmd', getter, 'json'),
                call('cmd', 'hasOption', 'xml'), call('second', 'hasOption', 'json')])
        additions.extend([
            setup() + [call('out', 'setOptionalArg', True), parse(['--output', '-v']),
                       call('cmd', 'hasOption', 'o'), call('cmd', 'getOptionValues', '--output')],
            setup() + [call('out', 'setArgs', 2), parse(['--output', 'one', 'two']),
                       parse(['-v'], save='second'), call('second', 'getOptionValue', 'output'),
                       call('cmd', 'getOptionValues', '--output')],
        ])
    rows = [dict(row, id=f'cli-v4-{split}-legacy-{i:02}') for i, row in enumerate(rows)]
    rows.extend({'id': f'cli-v4-{split}-{i:02}', 'task': 'commons_cli', 'operations': operations}
                for i, operations in enumerate(additions))
    validate_cases(rows, contract())
    return rows
