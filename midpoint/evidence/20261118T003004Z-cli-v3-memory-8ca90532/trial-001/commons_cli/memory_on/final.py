import copy


class ParseException(Exception):
    pass


class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matchingOptions):
        opts_str = ", ".join(f"'{opt}'" for opt in matchingOptions)
        msg = f"Ambiguous option: '{option}'  (could be: {opts_str})"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self):
        return list(self.matchingOptions)


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option = option_or_message
        else:
            super().__init__(str(option_or_message))
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_message):
        if isinstance(missingOptions_or_message, list):
            buf = ["Missing required option", "" if len(missingOptions_or_message) == 1 else "s", ": "]
            buf.append(", ".join(str(opt) for opt in missingOptions_or_message))
            super().__init__("".join(buf))
            self.missingOptions = list(missingOptions_or_message)
        else:
            super().__init__(str(missingOptions_or_message))
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message, option=None):
        if option is not None:
            group = group_or_message
            super().__init__(f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'")
            self.group = group
            self.option = option
        else:
            super().__init__(str(group_or_message))
            self.group = None
            self.option = None

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group


def _strip_leading_hyphens(s):
    if not s:
        return s
    if s.startswith("--"):
        return s[2:]
    if s.startswith("-"):
        return s[1:]
    return s


def _strip_leading_and_trailing_quotes(s):
    if not s:
        return s
    length = len(s)
    if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
        return s[1:length - 1]
    return s


class _OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def isValidChar(c):
        return c.isalnum() or c in ('$', '_') or c in _OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def isValidOpt(c):
        return c.isalnum() or c in ('$', '_') or c in _OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def validate(option):
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not _OptionValidator.isValidOpt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not _OptionValidator.isValidChar(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, opt, longOpt=None, hasArg=False, description=None):
        if isinstance(longOpt, bool) and description is None:
            description = hasArg
            hasArg = longOpt
            longOpt = None
        self.option = _OptionValidator.validate(opt)
        self.longOption = longOpt
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.values = []
        self.valueSeparator = '\0'
        if hasArg:
            self.argCount = 1
        else:
            self.argCount = Option.UNINITIALIZED

    def clone(self):
        cp = copy.copy(self)
        cp.values = list(self.values)
        return cp

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def setLongOpt(self, longOpt):
        self.longOption = longOpt

    def hasArg(self):
        return self.argCount > 0 or self.argCount == Option.UNLIMITED_VALUES

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = bool(required)

    def getValue(self, index=None):
        if not self.values:
            return None
        if index is None:
            return self.values[0]
        if 0 <= index < len(self.values):
            return self.values[index]
        raise IndexError("Index out of bounds")

    def getValues(self):
        return list(self.values) if self.values else None

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
        return self.option if self.option is not None else self.longOption

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == Option.UNLIMITED_VALUES

    def acceptsArg(self):
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self):
        if self.optionalArg:
            return False
        if self.argCount == Option.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def _add(self, val):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(val)

    def processValue(self, val):
        if self.argCount == Option.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = val
        if self.valueSeparator != '\0' and self.valueSeparator in add:
            sep = self.valueSeparator
            idx = add.find(sep)
            while idx != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add[:idx])
                add = add[idx + 1:]
                idx = add.find(sep)
        self._add(add)

    def clearValues(self):
        self.values.clear()

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self):
        return hash((self.longOption, self.option))

    def __str__(self):
        buf = [f"[ Option {self.option}"]
        if self.longOption is not None:
            buf.append(f" {self.longOption}")
        if self.hasArgs():
            buf.append("[ARG...]")
        elif self.hasArg():
            buf.append(" [ARG]")
        buf.append(f" :: {self.description} :: None ]")
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
        buf = ["["]
        first = True
        for option in self.getOptions():
            if not first:
                buf.append(", ")
            first = False
            if option.getOpt() is not None:
                buf.append(f"-{option.getOpt()}")
            else:
                buf.append(f"--{option.getLongOpt()}")
            if option.getDescription() is not None:
                buf.append(f" {option.getDescription()}")
        buf.append("]")
        return "".join(buf)


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt):
        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def addOptionGroup(self, group):
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
        return self

    def getMatchingOptions(self, opt):
        clean = _strip_leading_hyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matches = []
        for longOpt in self.longOpts:
            if longOpt.startswith(clean):
                matches.append(longOpt)
        return matches

    def getOption(self, opt):
        clean = _strip_leading_hyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getOptionGroup(self, opt):
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        return set(self.optionGroups.values())

    def getOptions(self):
        return list(self.shortOpts.values())

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def hasLongOption(self, opt):
        clean = _strip_leading_hyphens(opt)
        return clean in self.longOpts

    def hasOption(self, opt):
        clean = _strip_leading_hyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt):
        clean = _strip_leading_hyphens(opt)
        return clean in self.shortOpts


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

    def getOptions(self):
        return list(self.options)

    def resolveOption(self, opt):
        actual = _strip_leading_hyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt):
        if isinstance(opt, Option):
            return opt in self.options
        elif isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        else:
            resolved = self.resolveOption(opt)
            if resolved is None:
                return False
            return self.hasOption(resolved)

    def getOptionValue(self, opt, defaultValue=None):
        values = self.getOptionValues(opt)
        if values is not None and len(values) > 0:
            return values[0]
        return defaultValue

    def getOptionValues(self, opt):
        if opt is None:
            return None
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        option = opt if isinstance(opt, Option) else self.resolveOption(opt)
        if option is None:
            return None
        values = []
        for processedOption in self.options:
            if processedOption == option:
                values.extend(processedOption.getValuesList())
        return values if values else None


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
        return token.find('=')

    def parse(self, options, arguments, stopAtNonOption=False):
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
        t = _strip_leading_hyphens(token)
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
            matches.append(self.options.getOption(token).getLongOpt())
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
        if not matchingOpts:
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
        if not matchingOpts:
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

    def handleShortAndLongOption(self, hyphenToken):
        token = _strip_leading_hyphens(hyphenToken)
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
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def isArgument(self, token):
        return not self.isOption(token) or self.isNegativeNumber(token)

    def isJavaProperty(self, token):
        if not token:
            return False
        opt = token[:1]
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
            return token.startswith("-")
        except (ValueError, TypeError):
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
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return _strip_leading_and_trailing_quotes(token)
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return _strip_leading_and_trailing_quotes(token)
        return token

    def updateRequiredOptions(self, option):
        if option.isRequired():
            key = option.getKey()
            if key in self.expectedOpts:
                self.expectedOpts.remove(key)
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                if group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)
