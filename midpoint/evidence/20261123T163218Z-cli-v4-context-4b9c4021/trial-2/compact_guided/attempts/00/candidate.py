import copy


class ParseException(Exception):
    def __init__(self, message=None):
        super().__init__(str(message) if message is not None else "")
        self._message = message


class AlreadySelectedException(ParseException):
    def __init__(self, *args):
        if len(args) == 2 and isinstance(args[0], OptionGroup) and isinstance(args[1], Option):
            group, option = args
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(msg)
            self.group = group
            self.option = option
        elif len(args) == 1:
            super().__init__(args[0])
            self.group = None
            self.option = None
        else:
            super().__init__()
            self.group = None
            self.option = None

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group


class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matchingOptions):
        matches = list(matchingOptions)
        buf = [f"Ambiguous option: '{option}'  (could be: "]
        for i, opt in enumerate(matches):
            buf.append(f"'{opt}'")
            if i < len(matches) - 1:
                buf.append(", ")
        buf.append(")")
        super().__init__("".join(buf), option)
        self.matchingOptions = matches

    def getMatchingOptions(self):
        return list(self.matchingOptions)


class MissingArgumentException(ParseException):
    def __init__(self, opt_or_msg):
        if isinstance(opt_or_msg, Option):
            super().__init__(f"Missing argument for option: {opt_or_msg.getKey()}")
            self.option = opt_or_msg
        else:
            super().__init__(str(opt_or_msg))
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_opts_or_msg):
        if isinstance(missing_opts_or_msg, list):
            missing = missing_opts_or_msg
            buf = ["Missing required option", "" if len(missing) == 1 else "s", ": "]
            for i, opt in enumerate(missing):
                buf.append(str(opt))
                if i < len(missing) - 1:
                    buf.append(", ")
            super().__init__("".join(buf))
            self.missingOptions = list(missing)
        else:
            super().__init__(str(missing_opts_or_msg))
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions


class Util:
    EMPTY_STRING_ARRAY = []

    @staticmethod
    def isEmpty(s):
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingAndTrailingQuotes(s):
        if Util.isEmpty(s):
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
            return s[1:length - 1]
        return s

    @staticmethod
    def stripLeadingHyphens(s):
        if Util.isEmpty(s):
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-',)

    @staticmethod
    def _is_java_identifier_part(c):
        return c.isalnum() or c == '_' or c == '$'

    @staticmethod
    def isValidChar(c):
        return OptionValidator._is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def isValidOpt(c):
        return OptionValidator._is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def validate(option):
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not OptionValidator.isValidOpt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not OptionValidator.isValidChar(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option, longOption=None, hasArg=False, description=None):
        self.option = OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else Option.UNINITIALIZED
        self.description = description
        self.argName = None
        self.optionalArg = False
        self.required = False
        self.since = None
        self.values = []
        self.valueSeparator = '\0'

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def setLongOpt(self, longOpt):
        self.longOption = longOpt

    def hasArg(self):
        return self.argCount > 0 or self.argCount == Option.UNLIMITED_VALUES

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == Option.UNLIMITED_VALUES

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = bool(required)

    def getValue(self, index_or_default=None):
        if self.hasNoValues():
            return None if index_or_default is None or isinstance(index_or_default, int) else index_or_default
        if index_or_default is None:
            return self.values[0]
        if isinstance(index_or_default, int):
            return self.values[index_or_default]
        return self.values[0] if self.values[0] is not None else index_or_default

    def getValues(self):
        return None if self.hasNoValues() else list(self.values)

    def getValuesList(self):
        return self.values

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    def getArgName(self):
        return self.argName

    def setArgName(self, argName):
        self.argName = argName

    def hasLongOpt(self):
        return self.longOption is not None

    def hasOptionalArg(self):
        return self.optionalArg

    def setOptionalArg(self, optionalArg):
        self.optionalArg = bool(optionalArg)

    def getArgs(self):
        return self.argCount

    def setArgs(self, num):
        self.argCount = num

    def getKey(self):
        return self.longOption if self.option is None else self.option

    def acceptsArg(self):
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (
            self.argCount <= 0 or len(self.values) < self.argCount
        )

    def requiresArg(self):
        if self.optionalArg:
            return False
        if self.argCount == Option.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def hasNoValues(self):
        return len(self.values) == 0

    def hasValueSeparator(self):
        return ord(self.valueSeparator) > 0

    def getValueSeparator(self):
        return self.valueSeparator

    def setValueSeparator(self, sep):
        self.valueSeparator = sep

    def _add(self, value):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value):
        if self.argCount == Option.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = value
        if self.hasValueSeparator():
            sep = self.getValueSeparator()
            index = add.find(sep)
            while index != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add[:index])
                add = add[index + 1:]
                index = add.find(sep)
        self._add(add)

    def clearValues(self):
        self.values.clear()

    def clone(self):
        c = copy.copy(self)
        c.values = list(self.values)
        return c

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self):
        return hash((self.longOption, self.option))

    def __str__(self):
        buf = ["[ Option ", self.option or ""]
        if self.longOption is not None:
            buf.append(" ")
            buf.append(self.longOption)
        if self.hasArgs():
            buf.append("[ARG...]")
        elif self.hasArg():
            buf.append(" [ARG]")
        buf.append(" :: ")
        buf.append(str(self.description))
        buf.append(" :: ")
        buf.append("class java.lang.String")
        buf.append(" ]")
        return "".join(buf)


class OptionGroup:
    def __init__(self):
        self.optionMap = {}
        self.selected = None
        self.required = False

    def addOption(self, option):
        self.optionMap[option.getKey()] = option
        return self

    def getNames(self):
        return sorted(list(self.optionMap.keys()))

    def getOptions(self):
        return list(self.optionMap.values())

    def getSelected(self):
        return self.selected

    def isRequired(self):
        return self.required

    def isSelected(self):
        return self.selected is not None

    def setRequired(self, required):
        self.required = bool(required)

    def setSelected(self, option):
        if option is None:
            self.selected = None
            return
        if self.selected is not None and self.selected != option.getKey():
            raise AlreadySelectedException(self, option)
        self.selected = option.getKey()

    def __str__(self):
        buff = ["["]
        opts = self.getOptions()
        for i, option in enumerate(opts):
            if option.getOpt() is not None:
                buff.append("-")
                buff.append(option.getOpt())
            else:
                buff.append("--")
                buff.append(option.getLongOpt())
            if option.getDescription() is not None:
                buff.append(" ")
                buff.append(option.getDescription())
            if i < len(opts) - 1:
                buff.append(", ")
        buff.append("]")
        return "".join(buff)


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, *args):
        if len(args) == 1 and isinstance(args[0], Option):
            opt = args[0]
            key = opt.getKey()
            if opt.hasLongOpt():
                self.longOpts[opt.getLongOpt()] = opt
            if opt.isRequired():
                if key in self.requiredOpts:
                    self.requiredOpts.remove(key)
                self.requiredOpts.append(key)
            self.shortOpts[key] = opt
            return self
        elif len(args) in (2, 3, 4):
            if len(args) == 2:
                opt_str, desc = args
                return self.addOption(Option(opt_str, None, False, desc))
            elif len(args) == 3:
                opt_str, has_arg, desc = args
                return self.addOption(Option(opt_str, None, has_arg, desc))
            else:
                opt_str, long_opt, has_arg, desc = args
                return self.addOption(Option(opt_str, long_opt, has_arg, desc))
        raise ValueError("Invalid arguments for addOption")

    def addOptionGroup(self, group):
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
        return self

    def getMatchingOptions(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matching = []
        for longOpt in self.longOpts.keys():
            if longOpt.startswith(clean):
                matching.append(longOpt)
        return matching

    def getOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getOptionGroup(self, opt):
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        seen = set()
        res = []
        for g in self.optionGroups.values():
            if id(g) not in seen:
                seen.add(id(g))
                res.append(g)
        return res

    def getOptions(self):
        return list(self.shortOpts.values())

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def hasLongOption(self, opt):
        return Util.stripLeadingHyphens(opt) in self.longOpts

    def hasOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt):
        return Util.stripLeadingHyphens(opt) in self.shortOpts


class CommandLine:
    def __init__(self, args=None, options=None):
        self.args = list(args) if args is not None else []
        self.options = list(options) if options is not None else []

    def addArg(self, arg):
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt):
        if opt is not None:
            self.options.append(opt)

    def getArgs(self):
        return list(self.args)

    def getArgList(self):
        return list(self.args)

    def _resolveOption(self, opt):
        if opt is None:
            return None
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt):
        if isinstance(opt, Option):
            return opt in self.options
        elif isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        else:
            resolved = self._resolveOption(opt)
            if resolved is None:
                return False
            return self.hasOption(resolved)

    def getOptionValues(self, opt):
        if isinstance(opt, Option):
            values = []
            for processedOption in self.options:
                if processedOption == opt:
                    values.extend(processedOption.getValuesList())
            return values if len(values) > 0 else None
        elif isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        else:
            resolved = self._resolveOption(opt)
            if resolved is None:
                return None
            return self.getOptionValues(resolved)

    def getOptionValue(self, opt, defaultValue=None):
        if isinstance(opt, Option):
            values = self.getOptionValues(opt)
            ans = values[0] if values else None
            return ans if ans is not None else (defaultValue() if callable(defaultValue) else defaultValue)
        elif isinstance(opt, OptionGroup):
            values = self.getOptionValues(opt)
            ans = values[0] if values else None
            return ans if ans is not None else (defaultValue() if callable(defaultValue) else defaultValue)
        else:
            resolved = self._resolveOption(opt)
            if resolved is None:
                return defaultValue() if callable(defaultValue) else defaultValue
            return self.getOptionValue(resolved, defaultValue)


class DefaultParser:
    def __init__(self, allowPartialMatching=True, stripLeadingAndTrailingQuotes=None):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = stripLeadingAndTrailingQuotes
        self.cmd = None
        self.options = None
        self.stopAtNonOption = False
        self.currentToken = None
        self.currentOption = None
        self.skipParsing = False
        self.expectedOpts = []

    @staticmethod
    def indexOfEqual(token):
        return token.find("=")

    def parse(self, options, arguments, stopAtNonOption=False, properties=None):
        self.options = options
        self.stopAtNonOption = stopAtNonOption
        self.skipParsing = False
        self.currentOption = None
        self.expectedOpts = list(options.getRequiredOptions())
        for group in options.getOptionGroups():
            group.setSelected(None)
        self.cmd = CommandLine()

        if arguments is not None:
            for argument in arguments:
                self.handleToken(argument)

        self.checkRequiredArgs()
        self.handleProperties(properties)
        self.checkRequiredOptions()
        return self.cmd

    def checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self.isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def checkRequiredOptions(self):
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def getLongPrefix(self, token):
        t = Util.stripLeadingHyphens(token)
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def getMatchingLongOptions(self, token):
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            opt = self.options.getOption(token)
            if opt.getLongOpt() is not None:
                matches.append(opt.getLongOpt())
        return matches

    def handleConcatenatedOptions(self, token):
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self.handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            self.handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def handleLongOption(self, token):
        if self.indexOfEqual(token) == -1:
            self.handleLongOptionWithoutEqual(token)
        else:
            self.handleLongOptionWithEqual(token)

    def handleLongOptionWithEqual(self, token):
        pos = self.indexOfEqual(token)
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self.getMatchingLongOptions(opt)
        if len(matchingOpts) == 0:
            self.handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matchingOpts)
        else:
            key = opt if self.options.hasLongOption(opt) else matchingOpts[0]
            option = self.options.getOption(key)
            if option.acceptsArg():
                self.handleOption(option)
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(value))
                self.currentOption = None
            else:
                self.handleUnknownToken(self.currentToken)

    def handleLongOptionWithoutEqual(self, token):
        matchingOpts = self.getMatchingLongOptions(token)
        if len(matchingOpts) == 0:
            self.handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self.handleOption(self.options.getOption(key))

    def handleOption(self, option):
        self.checkRequiredArgs()
        copy_opt = option.clone()
        self.updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def handleProperties(self, properties):
        if properties is None:
            return
        for option, value in properties.items():
            opt = self.options.getOption(option)
            if opt is None:
                raise UnrecognizedOptionException("Default option wasn't defined", option)
            group = self.options.getOptionGroup(opt)
            selected = group is not None and group.isSelected()
            if not self.cmd.hasOption(option) and not selected:
                if opt.hasArg():
                    if opt.hasNoValues():
                        opt.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(value))
                elif str(value).lower() not in ("yes", "true", "1"):
                    continue
                self.handleOption(opt)
                self.currentOption = None

    def handleShortAndLongOption(self, hyphenToken):
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = self.indexOfEqual(token)
        if len(token) == 1:
            if self.options.hasShortOption(token):
                self.handleOption(self.options.getOption(token))
            else:
                self.handleUnknownToken(hyphenToken)
        elif pos == -1:
            if self.options.hasShortOption(token):
                self.handleOption(self.options.getOption(token))
            elif len(self.getMatchingLongOptions(token)) > 0:
                self.handleLongOptionWithoutEqual(hyphenToken)
            else:
                opt = self.getLongPrefix(token)
                if opt is not None and self.options.getOption(opt).acceptsArg():
                    self.handleOption(self.options.getOption(opt))
                    self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[len(opt):]))
                    self.currentOption = None
                elif self.isJavaProperty(token):
                    self.handleOption(self.options.getOption(token[:1]))
                    self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[1:]))
                    self.currentOption = None
                else:
                    self.handleConcatenatedOptions(hyphenToken)
        else:
            opt = token[:pos]
            value = token[pos + 1:]
            if len(opt) == 1:
                option = self.options.getOption(opt)
                if option is not None and option.acceptsArg():
                    self.handleOption(option)
                    self.currentOption.processValue(value)
                    self.currentOption = None
                else:
                    self.handleUnknownToken(hyphenToken)
            elif self.isJavaProperty(opt):
                self.handleOption(self.options.getOption(opt[:1]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self.handleLongOptionWithEqual(hyphenToken)

    def handleToken(self, token):
        if token is not None:
            self.currentToken = token
            if self.skipParsing:
                self.cmd.addArg(token)
            elif token == "--":
                self.skipParsing = True
            elif self.currentOption is not None and self.currentOption.acceptsArg() and self.isArgument(token):
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOn(token))
            elif token.startswith("--"):
                self.handleLongOption(token)
            elif token.startswith("-") and token != "-":
                self.handleShortAndLongOption(token)
            else:
                self.handleUnknownToken(token)
            if self.currentOption is not None and not self.currentOption.acceptsArg():
                self.currentOption = None

    def handleUnknownToken(self, token):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException("Unrecognized option: " + token, token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def isArgument(self, token):
        return not self.isOption(token) or self.isNegativeNumber(token)

    def isJavaProperty(self, token):
        opt = None if len(token) == 0 else token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def isLongOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self.indexOfEqual(token)
        t = token if pos == -1 else token[:pos]
        if len(self.getMatchingLongOptions(t)) > 0:
            return True
        if self.getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def isNegativeNumber(self, token):
        try:
            float(token)
            return True
        except ValueError:
            return False

    def isOption(self, token):
        return self.isLongOption(token) or self.isShortOption(token)

    def isShortOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self.indexOfEqual(token)
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[:1])

    def stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def updateRequiredOptions(self, option):
        if option.isRequired():
            key = option.getKey()
            if key in self.expectedOpts:
                self.expectedOpts.remove(key)
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)
