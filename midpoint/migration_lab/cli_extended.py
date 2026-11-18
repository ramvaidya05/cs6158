"""Frozen v3 CLI extension: group selection and option metadata/arity.

Evaluator-owned scenarios; never import into the model prompt builder.
"""
from .cli_task import new, call, ref, contract
from .cli_semantic import cases as previous_cases, setup, parse
from .scenarios import validate_cases

PROFILE = 'commons-cli-extended-v3'


def group_setup(required=False):
    return [new('Options','opts'), new('Option','json','j','json',False,'JSON'),
            new('Option','xml','x','xml',False,'XML'), new('OptionGroup','group'),
            call('group','addOption',ref('json'),save='alias'), call('alias','addOption',ref('xml')),
            call('group','setRequired',required),call('opts','addOptionGroup',ref('group'),save='optsAlias'),
            new('DefaultParser','parser',True)]


def cases(split, seed=6158):
    rows = previous_cases(split, seed)
    def add(name, ops):
        rows.append({'id':f'extended-v3-{split}-{name}','task':'commons_cli','operations':ops})
    if split == 'visible':
        add('metadata',setup()+[call('out','getDescription'),call('out','setDescription','changed'),call('out','getDescription'),
            call('out','getArgName'),call('out','setArgName','FILE'),call('out','getArgName'),call('out','hasLongOpt'),
            call('out','hasOptionalArg'),call('out','setOptionalArg',True),call('out','hasOptionalArg'),
            call('out','getArgs'),call('out','setArgs',2),call('out','getArgs'),
            call('opts','getMatchingOptions','out'),parse(['-o','first','second']),call('cmd','getOptionValues','o')])
        add('optional-value',setup()+[call('out','setOptionalArg',True),parse(['-o','-v']),call('cmd','hasOption','o'),call('cmd','getOptionValue','o')])
        add('group-metadata',group_setup()+[call('group','getNames'),call('group','getSelected'),call('group','isRequired'),
            call('group','setSelected',ref('json')),call('alias','getSelected')])
        add('group-select',group_setup(True)+[call('opts','getRequiredOptions'),parse(['-j']),call('group','getSelected'),call('cmd','hasOption','json')])
        add('group-conflict',group_setup()+[parse(['-j','-x'])])
        add('group-required-missing',group_setup(True)+[parse([])])
        add('group-reuse',group_setup()+[parse(['-j']),parse(['-x'],save='second'),call('group','getSelected'),call('cmd','hasOption','j'),call('second','hasOption','x')])
        add('direct-selection-conflict',group_setup()+[call('group','setSelected',ref('xml')),call('group','setSelected',ref('json'))])
    elif split == 'holdout':
        # State transitions and compositions differ from the visible scenarios.
        add('metadata-after-reuse',setup()+[call('out','setDescription',''),call('out','setArgName','DEST'),
            call('out','setRequired',True),call('out','isRequired'),call('out','setRequired',False),
            call('out','setArgs',2),call('out','getArgs'),call('out','setArgs',1),
            call('out','setOptionalArg',True),parse(['--output=held']),parse([],save='second'),
            call('out','getOpt'),call('out','getLongOpt'),call('out','hasArg'),call('out','getValue'),
            call('out','getDescription'),call('out','getArgName'),call('out','hasLongOpt'),
            call('out','hasOptionalArg'),call('out','setOptionalArg',False),call('out','hasOptionalArg'),
            call('cmd','getOptionValues','output'),call('opts','getMatchingOptions','--output')])
        add('group-repeated-selection',group_setup(True)+[call('group','isRequired'),call('group','getNames'),
            call('optsAlias','getRequiredOptions'),call('group','setSelected',ref('xml')),call('group','setSelected',ref('xml')),
            parse(['--xml','--xml']),call('group','getSelected'),call('cmd','hasOption','x')])
        add('group-reset-empty',group_setup()+[parse(['--json']),parse(['file'],save='second'),call('group','getSelected'),call('second','getArgs')])
        add('group-long-conflict',group_setup()+[parse(['--xml','--json'])])
        add('required-after-terminator',group_setup(True)+[parse(['--','--json'])])
        add('optional-toggle',setup()+[call('out','setOptionalArg',True),parse(['--output']),call('cmd','getOptionValue','o'),
            call('out','setOptionalArg',False),parse(['--output'],save='second')])
        add('two-values-then-flag',setup()+[call('out','setArgs',2),parse(['--output','alpha','beta','-v']),
            call('cmd','getOptionValues','o'),call('cmd','hasOption','v'),call('out','getValues')])
        add('group-required-toggle',group_setup()+[call('group','setRequired',True),call('group','isRequired'),
            call('group','setRequired',False),call('group','isRequired'),call('group','getNames'),parse([])])
    else:
        raise ValueError('Unknown split')
    validate_cases(rows,contract())
    return rows
