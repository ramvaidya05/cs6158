"""CSV v2: all inspected v1 cases are development; new composed holdout.

No model results are used to generate the new split. Seeds vary field payloads,
not the declared semantic strata. This is a scoped suite, not exhaustive proof.
"""
import copy
import random
from .csv_cases import cases as old_cases
from .csv_task import validate_cases

PROFILE = 'commons-csv-v2'


def cases(split='visible', seed=6158):
    if split not in ('visible', 'holdout'):
        raise ValueError('Unknown CSV split')
    rows = []
    def add(operation, label, value, **config):
        rows.append({'id': f'csv-v2-{split}-{label}', 'task': 'commons_csv',
                     'operation': operation, 'text' if operation == 'parse' else 'records': value,
                     'config': config})
    if split == 'visible':
        for i, case in enumerate(old_cases('visible') + old_cases('holdout')):
            row = copy.deepcopy(case)
            row['id'] = f'csv-v2-visible-promoted-{i:03}'
            rows.append(row)
        for suffix in ('r', 'n', 't', 'b', 'f', 'z', '\\', ',', '"'):
            add('parse', f'escape-{ord(suffix)}', 'left\\'+suffix+'right,end', escape='\\')
            add('parse', f'quoted-escape-{ord(suffix)}', '"left\\'+suffix+'right",end', escape='\\')
        for name in ('delimiter', 'quote', 'escape'):
            add('parse', name+'-utf16', 'data,tail', **{name:'😀'})
            add('print', name+'-utf16-output', [['data','tail']], **{name:'😀'})
        add('parse', 'terminal-escape', 'payload\\', escape='\\')
        add('parse', 'quoted-terminal-escape', '"payload\\', escape='\\')
        for i, space in enumerate(('\x00', '\t', '\u00a0', '\u2003', '\u202f')):
            add('parse', f'trim-{i}', space+'x'+space+',"'+space+'y'+space+'"', trim=True)
            add('parse', f'surrounding-{i}', space+'x'+space+',z', ignore_surrounding_spaces=True)
    else:
        rng = random.Random(seed ^ 0xC5A2026)
        # Different values and compositions from all previous development cases.
        for i, delim in enumerate(('|', ':', '\t')):
            marker = 'item'+str(rng.randrange(10000, 99999))
            for j, suffix in enumerate(('r', 'n', 't', 'b', 'f', 'q', delim)):
                text = '"'+marker+'!'+suffix+'Ω"'+delim+'tail!'+suffix+'end\r\n'
                add('parse', f'composed-escape-{i}-{j}', text, delimiter=delim, escape='!')
            add('parse', f'escaped-physical-{i}', marker+'!\nnext'+delim+'x!\ry', delimiter=delim, escape='!')
            add('parse', f'escape-eof-{i}', 'ok'+delim+'unfinished!', delimiter=delim, escape='!')
        for i, name in enumerate(('delimiter', 'quote', 'escape')):
            add('parse', f'character-validation-{i}', 'fresh;record', **{'delimiter':';', name:'🧪'})
            add('print', f'printer-character-validation-{i}', [['fresh',None]], **{name:'𐐀'})
        for i, mode in enumerate(('ALL', 'ALL_NON_NULL', 'MINIMAL', 'NON_NUMERIC', 'NONE')):
            config = {'quote_mode':mode, 'null_string':'absent', 'delimiter':'|', 'escape':'!', 'record_separator':'\n'}
            add('print', f'mode-composition-{i}', [[None,'absent','','x|y'],['a!b','c"d','line\r\nnext','  edge  ']], **config)
            add('parse', f'null-composition-{i}', 'absent|"absent"|""|\n"v|w"|absent|tail|', **config)
        for i, space in enumerate(('\u00a0', '\u2002', '\u202f', '\x1f')):
            add('parse', f'space-composition-{i}', space+'one'+space+';"'+space+'two'+space+'";\r\n', delimiter=';', trim=True, ignore_surrounding_spaces=True)
            add('print', f'print-space-{i}', [[space+'one'+space, '', None]], trim=True, delimiter=':', null_string='nil')
        add('parse', 'retained-blanks', '\r\n"fresh|value"|\r\n\r\nlast|""\r\n', delimiter='|', ignore_empty_lines=False)
        add('parse', 'malformed-after-quote', 'ok|row\n"fresh"unexpected|tail', delimiter='|')
        add('parse', 'quote-disabled-composition', "'x'|a!|b|", delimiter='|', quote=None, escape='!')
        add('print', 'custom-quote-composition', [["it's|quoted",'a!b',None],[]], delimiter='|', quote="'", escape='!', null_string='nil', record_separator='\r')
        add('print', 'disabled-quote-composition', [['x|y','a!b','c\nd']], delimiter='|', quote=None, escape='!')
        for i, name in enumerate(('trim', 'ignore_surrounding_spaces', 'ignore_empty_lines')):
            add('print', f'bool-validation-{i}', [['fresh']], **{name:0})
    validate_cases(rows)
    return rows
