import copy


class ParseException(Exception):
    """Base for Exceptions thrown during parsing of a command-line."""
    def __init__(self, message_or_cause):
        super().__init__(str(message_or_cause))
        self.message = str(message_or_cause)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matching_options):
        opts_str = ", ".join(f"'{opt}'" for opt in matching_options)
        msg = f"Ambiguous option: '{option}'  (could be: {opts_str})"
        super().__init__(msg, option)
        self.matchingOptions = list(matching_options)

    def getMatchingOptions(self):
        return self.matchingOptions


class MissingOptionException(ParseException):
    def __init__(self, missing_options):
        if isinstance(missing_options, list):
            suffix = "" if len(missing_options) == 1 else "s"
            items_str = ", ".join(str(item) for item in missing_options)
            msg = f"Missing required option{suffix}: {items_str}"
            super().__init__(msg)
            self.missingOptions = missing_options
        else:
            super().__init__(missing_options)
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions


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


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message, option=None):
        if option is not None:
            group = group_or_message
            super().__init__(
                f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            )
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


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-',)

    @staticmethod
    def is_java_identifier_part(c):
        return c.isalnum() or c in ('$', '_')

    @classmethod
    def isValidChar(cls, c):
        return cls.is_java_identifier_part(c) or c in cls.ADDITIONAL_LONG_CHARS

    @classmethod
    def isValidOpt(cls, c):
        return cls.is_java_identifier_part(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def validate(cls, option):
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not cls.isValidOpt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not cls.isValidChar(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class Util:
    @staticmethod
    def stripLeadingHyphens(s):
        if not s:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s):
        if not s:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:-1].find('"') == -1:
            return s[1:-1]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option, longOption=None, hasArg=False, description=None):
        self.option = OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.values = []
        self.valueSeparator = '\0'

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def setLongOpt(self, longOpt):
        self.longOption = longOpt

    def hasLongOpt(self):
        return self.longOption is not None

    def hasArg(self):
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = bool(required)

    def getValue(self, index_or_default=None):
        if index_or_default is None:
            return None if not self.values else self.values[0]
        if isinstance(index_or_default, int):
            if not self.values or index_or_default < 0 or index_or_default >= len(self.values):
                return None
            return self.values[index_or_default]
        val = self.getValue()
        return val if val is not None else index_or_default

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
        if self.argCount == self.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def hasValueSeparator(self):
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def getValueSeparator(self):
        return self.valueSeparator

    def setValueSeparator(self, sep):
        self.valueSeparator = sep

    def clearValues(self):
        self.values.clear()

    def processValue(self, value):
        if self.argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = value
        if self.hasValueSeparator():
            sep = self.valueSeparator
            index = add.find(sep)
            while index != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add[:index])
                add = add[index + 1:]
                index = add.find(sep)
        self._add(add)

    def _add(self, value):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def clone(self):
        cloned = copy.copy(self)
        cloned.values = list(self.values)
        return cloned

    def __copy__(self):
        c = Option.__new__(Option)
        c.option = self.option
        c.longOption = self.longOption
        c.argCount = self.argCount
        c.description = self.description
        c.required = self.required
        c.optionalArg = self.optionalArg
        c.argName = self.argName
        c.values = list(self.values)
        c.valueSeparator = self.valueSeparator
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
        buf = ["[ Option ", str(self.option)]
        if self.longOption is not None:
            buf.append(f" {self.longOption}")
        if self.hasArgs():
            buf.append("[ARG...]")
        elif self.hasArg():
            buf.append(" [ARG]")
        buf.append(f" :: {self.description} :: class java.lang.String ]")
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
        return sorted(self.optionMap.keys())

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
        options = list(self.getOptions())
        for idx, option in enumerate(options):
            if option.getOpt() is not None:
                buff.append("-")
                buff.append(option.getOpt())
            else:
                buff.append("--")
                buff.append(option.getLongOpt())
            if option.getDescription() is not None:
                buff.append(" ")
                buff.append(option.getDescription())
            if idx < len(options) - 1:
                buff.append(", ")
        buff.append("]")
        return "".join(buff)


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt_or_str, *args):
        if isinstance(opt_or_str, Option):
            opt = opt_or_str
            key = opt.getKey()
            if opt.hasLongOpt():
                self.longOpts[opt.getLongOpt()] = opt
            if opt.isRequired():
                if key in self.requiredOpts:
                    self.requiredOpts.remove(key)
                self.requiredOpts.append(key)
            self.shortOpts[key] = opt
            return self
        elif len(args) == 2:
            hasArg, description = args
            return self.addOption(Option(opt_or_str, None, hasArg, description))
        elif len(args) == 1:
            description = args[0]
            return self.addOption(Option(opt_or_str, None, False, description))
        elif len(args) == 3:
            longOpt, hasArg, description = args
            return self.addOption(Option(opt_or_str, longOpt, hasArg, description))
        raise ValueError("Invalid arguments for addOption")

    def addOptionGroup(self, group):
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
        return self

    def hasOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasLongOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def hasShortOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def getOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def getMatchingOptions(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matching = []
        for longOpt in self.longOpts.keys():
            if longOpt.startswith(clean):
                matching.append(longOpt)
        return matching

    def getOptionGroup(self, opt):
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        return list(set(self.optionGroups.values()))

    def getOptions(self):
        return list(self.shortOpts.values())


class CommandLine:
    def __init__(self, args, options):
        self.args = list(args)
        self.options = list(options)

    def hasOption(self, opt):
        option = self._resolveOption(opt)
        return option in self.options if option is not None else False

    def getOptionValue(self, opt, defaultValue=None):
        option = self._resolveOption(opt)
        values = self.getOptionValues(option) if option is not None else None
        if values is not None and len(values) > 0:
            return values[0]
        return defaultValue

    def getOptionValues(self, opt):
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        if isinstance(opt, Option):
            option = opt
        else:
            option = self._resolveOption(opt)
        if option is None:
            return None
        values = []
        for processedOption in self.options:
            if processedOption == option:
                values.extend(processedOption.getValuesList())
        return values if values else None

    def getArgs(self):
        return list(self.args)

    def _resolveOption(self, opt):
        if isinstance(opt, Option):
            return opt
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None


class DefaultParser:
    def __init__(self, allowPartialMatching=True):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = None
        self.cmd = None
        self.options = None
        self.stopAtNonOption = False
        self.currentToken = None
        self.currentOption = None
        self.skipParsing = False
        self.expectedOpts = None

    def parse(self, options, arguments, stopAtNonOption=False):
        self.options = options
        self.stopAtNonOption = stopAtNonOption
        self.skipParsing = False
        self.currentOption = None
        self.expectedOpts = list(options.getRequiredOptions())

        for group in options.getOptionGroups():
            group.setSelected(None)

        self.cmd = CommandLine([], [])
        if arguments is not None:
            for argument in arguments:
                self._handleToken(argument)

        self._checkRequiredArgs()
        self._checkRequiredOptions()
        return self.cmd

    def _checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self):
        if self.expectedOpts and len(self.expectedOpts) > 0:
            raise MissingOptionException(list(self.expectedOpts))

    def _isJavaProperty(self, token):
        opt = None if not token else token[0:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _getLongPrefix(self, token):
        t = Util.stripLeadingHyphens(token)
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def _getMatchingLongOptions(self, token):
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def _handleConcatenatedOptions(self, token):
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self._handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            self._handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def _handleLongOption(self, token):
        if "=" not in token:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleLongOptionWithEqual(self, token):
        pos = token.find("=")
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self._getMatchingLongOptions(opt)
        if not matchingOpts:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matchingOpts)
        else:
            key = opt if self.options.hasLongOption(opt) else matchingOpts[0]
            option = self.options.getOption(key)
            if option.acceptsArg():
                self._handleOption(option)
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(value))
                self.currentOption = None
            else:
                self._handleUnknownToken(self.currentToken)

    def _handleLongOptionWithoutEqual(self, token):
        matchingOpts = self._getMatchingLongOptions(token)
        if not matchingOpts:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleOption(self, option):
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.options.append(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _handleShortAndLongOption(self, hyphenToken):
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = token.find("=")
        if len(token) == 1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            else:
                self._handleUnknownToken(hyphenToken)
        elif pos == -1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            elif len(self._getMatchingLongOptions(token)) > 0:
                self._handleLongOptionWithoutEqual(hyphenToken)
            else:
                opt = self._getLongPrefix(token)
                if opt is not None and self.options.getOption(opt).acceptsArg():
                    self._handleOption(self.options.getOption(opt))
                    self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[len(opt):]))
                    self.currentOption = None
                elif self._isJavaProperty(token):
                    self._handleOption(self.options.getOption(token[0:1]))
                    self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[1:]))
                    self.currentOption = None
                else:
                    self._handleConcatenatedOptions(hyphenToken)
        else:
            opt = token[:pos]
            value = token[pos + 1:]
            if len(opt) == 1:
                option = self.options.getOption(opt)
                if option is not None and option.acceptsArg():
                    self._handleOption(option)
                    self.currentOption.processValue(value)
                    self.currentOption = None
                else:
                    self._handleUnknownToken(hyphenToken)
            elif self._isJavaProperty(opt):
                self._handleOption(self.options.getOption(opt[0:1]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self._handleLongOptionWithEqual(hyphenToken)

    def _handleToken(self, token):
        if token is not None:
            self.currentToken = token
            if self.skipParsing:
                self.cmd.args.append(token)
            elif token == "--":
                self.skipParsing = True
            elif self.currentOption is not None and self.currentOption.acceptsArg() and self._isArgument(token):
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOn(token))
            elif token.startswith("--"):
                self._handleLongOption(token)
            elif token.startswith("-") and token != "-":
                self._handleShortAndLongOption(token)
            else:
                self._handleUnknownToken(token)
            if self.currentOption is not None and not self.currentOption.acceptsArg():
                self.currentOption = None

    def _handleUnknownToken(self, token):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.args.append(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _isArgument(self, token):
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isOption(self, token):
        return self._isLongOption(token) or self._isShortOption(token)

    def _isLongOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        t = token if pos == -1 else token[:pos]
        if len(self._getMatchingLongOptions(t)) > 0:
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isShortOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _isNegativeNumber(self, token):
        try:
            float(token)
            return True
        except ValueError:
            return False

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _updateRequiredOptions(self, option):
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())

        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                if group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)
