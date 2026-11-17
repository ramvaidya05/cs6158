"""Deliberately broken parser-reuse qualification fixture for the declared CLI scenarios, not LLM output.

This is not a complete Commons CLI port. It exercises the trusted adapters and
repair controller; qualification success must never be reported as model accuracy.
"""
class ParseException(Exception): pass
class MissingArgumentException(ParseException): pass
class MissingOptionException(ParseException): pass
class UnrecognizedOptionException(ParseException): pass
class AmbiguousOptionException(ParseException): pass

class Option:
    def __init__(self, opt, long_opt, has_arg, description):
        self.opt, self.long_opt = opt, long_opt
        self.has_arg, self.description = has_arg, description
        self.required, self.values = False, []
    def getOpt(self): return self.opt
    def getLongOpt(self): return self.long_opt
    def hasArg(self): return self.has_arg
    def isRequired(self): return self.required
    def setRequired(self, required): self.required = required
    def getValue(self): return self.values[0] if self.values else None
    def getValues(self): return list(self.values) if self.values else None

class Options:
    def __init__(self):
        self.short, self.long, self.required = {}, {}, []
    def addOption(self, option):
        self.short[option.opt] = option
        self.long[option.long_opt] = option
        if option.required:
            if option.opt in self.required: self.required.remove(option.opt)
            self.required.append(option.opt)
        return self
    def hasOption(self, name):
        name = name[2:] if name.startswith('--') else name[1:] if name.startswith('-') else name
        return name in self.short or name in self.long
    def getRequiredOptions(self): return list(self.required)
    def lookup(self, name, partial=False):
        if name in self.short: return self.short[name]
        if name in self.long: return self.long[name]
        matches = [v for k, v in self.long.items() if k.startswith(name)] if partial else []
        if len(matches) > 1: raise AmbiguousOptionException(name)
        return matches[0] if matches else None

class CommandLine:
    def __init__(self): self.options, self.args = [], []
    def matching(self, name):
        name = name[2:] if name.startswith('--') else name[1:] if name.startswith('-') else name
        return [o for o in self.options if name in (o.opt, o.long_opt)]
    def hasOption(self, name): return bool(self.matching(name))
    def getOptionValues(self, name):
        values = [v for o in self.matching(name) for v in o.values]
        return values or None
    def getOptionValue(self, name):
        values = self.getOptionValues(name)
        return values[0] if values else None
    def getArgs(self): return list(self.args)

class DefaultParser:
    def __init__(self, allow_partial): self.allow_partial = allow_partial
    def parse(self, options, arguments, stop):
        command = getattr(self, "previous", None) or CommandLine()
        self.previous = command
        index = 0
        def add(option, value=None):
            clone = Option(option.opt, option.long_opt, option.has_arg, option.description)
            clone.values = [] if value is None else [value]
            command.options.append(clone)
        while index < len(arguments):
            token = arguments[index]
            index += 1
            if token == '--':
                command.args.extend(arguments[index:]); break
            if not token.startswith('-') or token == '-':
                command.args.append(token)
                if stop: command.args.extend(arguments[index:]); break
                continue
            name, equals, attached = token.lstrip('-').partition('=')
            option = options.lookup(name, self.allow_partial)
            if option is None and not token.startswith('--') and len(name) > 1:
                # Short-option bursting; argument-bearing option consumes the tail.
                position = 0
                while position < len(name):
                    option = options.short.get(name[position])
                    if option is None: break
                    position += 1
                    if option.has_arg:
                        attached, equals = name[position:], bool(name[position:])
                        break
                    add(option)
                if position == len(name) and option is not None and not option.has_arg:
                    continue
            if option is None:
                if stop:
                    command.args.extend([token] + arguments[index:]); break
                raise UnrecognizedOptionException(token)
            if option.has_arg:
                if equals:
                    value = attached
                else:
                    if index >= len(arguments): raise MissingArgumentException(token)
                    value = arguments[index]
                    if value.startswith('-') and options.hasOption(value): raise MissingArgumentException(token)
                    index += 1
                add(option, value)
            else:
                if equals: raise UnrecognizedOptionException(token)
                add(option)
        if any(not command.hasOption(name) for name in options.required):
            raise MissingOptionException('required option absent')
        return command
