"""Evaluator-owned semantic scenarios; never included in translation prompts.

Holdout sequences are authored separately, not renamed copies of visible ones.
They share API concepts, so they are not independent repositories or proof of
out-of-distribution generalization. Test design is fixed before live generation.
"""
from .cli_task import new, call, ref, contract, cases as pilot_cases
from .scenarios import validate_cases

PROFILE = 'commons-cli-semantic-v2'


def setup(partial=True):
    return [new('Options','opts'), new('Option','out','o','output',True,'output'),
            new('Option','verbose','v','verbose',False,'verbose'),
            call('opts','addOption',ref('out'),save='alias'),
            call('alias','addOption',ref('verbose')),new('DefaultParser','parser',partial)]


def parse(args, save='cmd', stop=False, opts='opts'):
    return call('parser','parse',ref(opts),args,stop,save=save)


def cases(split, seed=6158):
    # Fixed semantic definitions; seed is intentionally unused in this profile.
    if split not in ('visible','holdout'): raise ValueError('Unknown split')
    rows = pilot_cases('visible') if split == 'visible' else []
    def add(label, ops):
        rows.append({'id':f'semantic-v2-{split}-{label}','task':'commons_cli','operations':ops})
    if split == 'visible':
        add('unique-prefix',setup()+[parse(['--out','prefix']),call('cmd','getOptionValue','output')])
        add('ambiguous-prefix',setup()+[new('Option','other','p','outline',False,'other'),call('opts','addOption',ref('other')),parse(['--out'])])
        add('partial-disabled',setup(False)+[parse(['--out','x'])])
        add('exact-over-prefix',setup()+[new('Option','other','p','outputting',False,'other'),call('opts','addOption',ref('other')),parse(['--output','x']),call('cmd','getOptionValue','o')])
        add('quoted-value',setup()+[parse(['-o','"two words"']),call('cmd','getOptionValue','o')])
        add('quoted-equals',setup()+[parse(['--output="two words"']),call('cmd','getOptionValue','o')])
        add('dash-as-value',setup()+[parse(['-o','-']),call('cmd','getOptionValue','o')])
        add('flag-equals',setup()+[parse(['--verbose=yes'])])
        add('replacement',setup()+[new('Option','replacement','o','replacement',False,'new'),call('opts','addOption',ref('replacement')),parse(['-o']),call('cmd','hasOption','replacement'),call('cmd','hasOption','output')])
        add('same-long-name',setup()+[new('Option','replacement','p','output',False,'new'),call('opts','addOption',ref('replacement')),parse(['--output']),call('cmd','hasOption','p'),call('cmd','hasOption','o')])
        add('required-after-add',setup()+[call('out','setRequired',True),call('opts','getRequiredOptions'),parse([])])
        add('required-after-readd',setup()+[call('out','setRequired',True),call('opts','addOption',ref('out')),call('out','setRequired',False),call('opts','getRequiredOptions'),parse([])])
        add('parse-with-another-options',setup()+[parse(['-o','first']),new('Options','other'),parse([],save='second',opts='other'),call('cmd','getOptionValue','o'),call('second','getOptionValue','o')])
        add('stop-reset',setup()+[parse(['file','-v'],stop=True),parse(['-v'],save='second'),call('cmd','getArgs'),call('second','hasOption','v')])
        add('ordered-values',setup()+[parse(['-o','third','-o','first','-o','second']),call('cmd','getOptionValues','o')])
        add('invalid-option-name',[new('Option','invalid','bad!','bad',False,'invalid')])
    else:
        # Distinct compositions from the visible scenarios, with explicit oracles.
        add('prefix-equals-and-repetition',setup()+[parse(['--out=one','--output=two']),call('cmd','getOptionValues','output')])
        add('ambiguity-with-equals',setup()+[new('Option','other','p','outlier',True,'other'),call('opts','addOption',ref('other')),parse(['--out=value'])])
        add('disabled-prefix-stop',setup(False)+[parse(['--out=value','-v'],stop=True),call('cmd','getArgs'),call('cmd','hasOption','v')])
        add('exact-prefix-flag',setup()+[new('Option','shortlong','p','out',False,'exact'),call('opts','addOption',ref('shortlong')),parse(['--out','-o','x']),call('cmd','hasOption','p'),call('cmd','getOptionValue','output')])
        add('quotes-empty-and-repeat',setup()+[parse(['-o','""','-o',"'a b'",'-o','']),call('cmd','getOptionValues','o')])
        add('quotes-embedded-equals',setup()+[parse(['--output="a=b c"']),call('cmd','getOptionValue','output')])
        add('terminator-after-value',setup()+[parse(['-o','-', '--','-o','ignored','--verbose']),call('cmd','getOptionValue','o'),call('cmd','getArgs'),call('cmd','hasOption','v')])
        add('flag-equals-stop',setup()+[parse(['--verbose=yes','-o','ignored'],stop=True),call('cmd','getArgs'),call('cmd','hasOption','v')])
        add('replacement-retains-long-map',setup()+[new('Option','replacement','o','new-output',False,'new'),call('alias','addOption',ref('replacement')),call('opts','hasOption','output'),parse(['--output','old','--new-output']),call('cmd','getOptionValues','o'),call('cmd','hasOption','new-output')])
        add('same-long-different-short-paths',setup()+[new('Option','replacement','p','output',False,'new'),call('opts','addOption',ref('replacement')),parse(['-o','old','--output']),call('cmd','hasOption','p'),call('cmd','getOptionValues','o')])
        add('required-list-snapshot',setup()+[call('opts','getRequiredOptions'),call('out','setRequired',True),call('opts','addOption',ref('out')),call('opts','getRequiredOptions'),parse(['-o','ok']),call('cmd','getOptionValue','o')])
        add('required-replacement',setup()+[call('out','setRequired',True),call('opts','addOption',ref('out')),new('Option','replacement','o','new',False,'new'),call('opts','addOption',ref('replacement')),call('opts','getRequiredOptions'),parse(['--new']),call('cmd','hasOption','new')])
        add('three-parses-two-configurations',setup()+[parse(['-o','alpha']),new('Options','empty'),parse(['file'],save='second',opts='empty'),parse(['-v','-o','beta'],save='third'),call('cmd','getOptionValue','o'),call('second','getArgs'),call('third','getOptionValue','o'),call('out','getValues')])
        add('stop-mode-switch',setup()+[parse(['unknown','-v'],stop=True),parse(['file','-v'],save='second'),call('second','hasOption','v'),call('second','getArgs'),call('cmd','hasOption','v')])
        add('repeated-empty-unicode',setup()+[parse(['-o','🚀','--output=','-o','é']),call('cmd','getOptionValue','o'),call('cmd','getOptionValues','output'),call('out','getValues')])
        add('invalid-space-short',[new('Option','invalid','two words','long-name',True,'invalid')])
        add('alias-after-new-option',setup()+[new('Option','late','l','late',False,'late'),call('alias','addOption',ref('late'),save='again'),parse(['-l']),call('cmd','hasOption','late'),call('again','hasOption','l')])
        add('required-two-missing-one',setup()+[call('out','setRequired',True),call('verbose','setRequired',True),call('opts','addOption',ref('out')),call('opts','addOption',ref('verbose')),parse(['-o','x'])])
        add('negative-and-positional',setup()+[parse(['-o','-2.5','tail','-v']),call('cmd','getOptionValue','o'),call('cmd','getArgs'),call('cmd','hasOption','verbose')])
        add('unknown-after-known',setup()+[parse(['-v','--missing'])])
    validate_cases(rows,contract())
    return rows
