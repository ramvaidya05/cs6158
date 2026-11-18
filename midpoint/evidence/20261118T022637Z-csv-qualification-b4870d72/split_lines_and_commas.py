"""Synthetic stdlib probe, NOT a claimed complete Commons CSV translation.

Known differences are retained and reported by qualification, never hidden.
"""
import csv
import io

class CSVParseError(Exception): pass
class IllegalArgumentException(Exception): pass


def settings(config):
    delimiter=config.get('delimiter',',');quote=config.get('quote','"');escape=config.get('escape')
    for key,value in [('delimiter',delimiter),('quote',quote),('escape',escape)]:
        if value is None and key!='delimiter':continue
        if not isinstance(value,str) or len(value.encode('utf-16-le'))!=2 or value in ('\r','\n'):
            raise IllegalArgumentException()
    if delimiter==quote or delimiter==escape:raise IllegalArgumentException()
    for key in ('ignore_empty_lines','ignore_surrounding_spaces','trim'):
        if key in config and type(config[key]) is not bool:raise IllegalArgumentException()
    mode=config.get('quote_mode','MINIMAL')
    if mode not in ('ALL','ALL_NON_NULL','MINIMAL','NON_NUMERIC','NONE') or (mode=='NONE' and escape is None):
        raise IllegalArgumentException()
    return delimiter,quote,escape,mode


def parse_csv(text,config):
    delimiter,quote,escape,mode=settings(config)
    try:
        reader=csv.reader(io.StringIO(text,newline=''),delimiter=delimiter,quotechar=quote,
            escapechar=escape,quoting=csv.QUOTE_NONE if quote is None else csv.QUOTE_MINIMAL,
            skipinitialspace=config.get('ignore_surrounding_spaces',False),strict=True)
        result=[]
        for row in reader:
            if not row:
                if config.get('ignore_empty_lines',True):continue
                row=['']
            if config.get('trim',False):row=[v.strip() for v in row]
            if config.get('null_string') is not None:row=[None if v==config['null_string'] else v for v in row]
            result.append(row)
        return result
    except csv.Error as exc:raise CSVParseError(str(exc))


def print_csv(records,config):
    delimiter,quote,escape,mode=settings(config)
    quoting={'MINIMAL':csv.QUOTE_MINIMAL,'ALL':csv.QUOTE_ALL,'ALL_NON_NULL':csv.QUOTE_ALL,
             'NON_NUMERIC':csv.QUOTE_NONNUMERIC,'NONE':csv.QUOTE_NONE}[mode]
    if quote is None:quoting=csv.QUOTE_NONE
    out=io.StringIO(newline='')
    try:
        writer=csv.writer(out,delimiter=delimiter,quotechar=quote,escapechar=escape,quoting=quoting,
                          lineterminator=config.get('record_separator','\r\n'))
        for row in records:
            values=[config.get('null_string') if v is None else v.strip() if config.get('trim',False) else v for v in row]
            writer.writerow(values)
        return out.getvalue()
    except csv.Error as exc:raise CSVParseError(str(exc))

def parse_csv(text, config): return [line.split(",") for line in text.splitlines()]
