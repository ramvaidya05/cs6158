import copy


class ParseException(Exception):
    def __init__(self, message_or_cause=""):
        super().__init__(str(message_or_cause))
        self.cause = message_or_cause if isinstance(message_or_cause, BaseException) else None

    @staticmethod
    def wrap(e):
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg, option=None):
        if option is not None:
            super().__init__(
                f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_msg.getSelected()}'"
            )
            self.group = group_or_msg
            self.option = option
        else:
            super().__init__(group_or_msg)
            self.group = None
            self.option = None

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matchingOptions):
        buf = f"Ambiguous option: '{option}'  (could be: "
        buf += ", ".join(f"'{m}'" for m in matchingOptions)
        buf += ")"
        super().__init__(buf, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self):
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, option_or_msg):
        if isinstance(option_or_msg, Option):
            super().__init__(f"Missing argument for option: {option_or_msg.getKey()}")
            self.option = option_or_msg
        else:
            super().__init__(str(option_or_msg))
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_msg):
        if isinstance(missingOptions_or_msg, list):
            buf = "Missing required option" + ("" if len(missingOptions_or_msg) == 1 else "s") + ": "
            buf += ", ".join(str(o) for o in missingOptions_or_msg)
            super().__init__(buf)
            self.missingOptions = list(missingOptions_or_msg)
        else:
            super().__init__(str(missingOptions_or_msg))
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions


class _Util:
    @staticmethod
    def isEmpty(s):
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingAndTrailingQuotes(str_val):
        if _Util.isEmpty(str_val):
            return str_val
        length = len(str_val)
        if length > 1 and str_val.startswith('"') and str_val.endswith('"') and '"' not in str_val[1:length - 1]:
            return str_val[1:length - 1]
        return str_val

    @staticmethod
    def stripLeadingHyphens(str_val):
        if _Util.isEmpty(str_val):
            return str_val
        if str_val.startswith("--"):
            return str_val[2:]
        if str_val.startswith("-"):
            return str_val[1:]
        return str_val


class _OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def isValidChar(c):
        return (c.isalnum() or c in ('$', '_', '-') or (len(c) == 1 and ord(c) < 32))

    @staticmethod
    def isValidOpt(c):
        return (c.isalnum() or c in ('$', '_') or c in _OptionValidator.ADDITIONAL_OPTION_CHARS or (len(c) == 1 and ord(c) < 32))

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


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option, longOption=None, hasArg=False, description=None):
        if isinstance(option, str) and isinstance(longOption, bool):
            # Option(opt, hasArg, description)
            description = hasArg
            hasArg = longOption
            longOption = None

        self.option = _OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.type = str
        self.values = []
        self.valueSeparator = '\0'
        self.since = None
        self.deprecated = None
        self.converter = None

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def hasArg(self):
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = bool(required)

    def getValue(self, index_or_default=None):
        if index_or_default is None:
            return None if len(self.values) == 0 else self.values[0]
        if isinstance(index_or_default, int):
            if len(self.values) == 0:
                return None
            return self.values[index_or_default]
        val = self.getValue()
        return val if val is not None else index_or_default

    def getValues(self):
        return None if len(self.values) == 0 else list(self.values)

    def getValuesList(self):
        return self.values

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

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def hasOptionalArg(self):
        return self.optionalArg

    def hasLongOpt(self):
        return self.longOption is not None

    def hasValueSeparator(self):
        return self.valueSeparator != '\0'

    def getValueSeparator(self):
        return self.valueSeparator

    def getArgs(self):
        return self.argCount

    def isDeprecated(self):
        return self.deprecated is not None

    def _add(self, value):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value):
        if self.argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        to_add = value
        if self.hasValueSeparator():
            sep = self.valueSeparator
            idx = to_add.find(sep)
            while idx != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(to_add[:idx])
                to_add = to_add[idx + 1:]
                idx = to_add.find(sep)
        self._add(to_add)

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
        return self.option == other.option and self.longOption == other.longOption

    def __hash__(self):
        return hash((self.option, self.longOption))

    def __str__(self):
        return self.getKey() or ""


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt_or_short, *args):
        if isinstance(opt_or_short, Option):
            opt = opt_or_short
        else:
            if len(args) == 1:
                opt = Option(opt_or_short, None, False, args[0])
            elif len(args) == 2:
                opt = Option(opt_or_short, None, args[0], args[1])
            elif len(args) == 3:
                opt = Option(opt_or_short, args[0], args[1], args[2])
            else:
                raise ValueError("Invalid arguments for addOption")

        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def hasOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasLongOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def hasShortOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def getOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        return self.shortOpts.get(clean, self.longOpts.get(clean))

    def getMatchingOptions(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        return [long_opt for long_opt in self.longOpts if long_opt.startswith(clean)]

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def getOptionGroup(self, opt):
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        return set(self.optionGroups.values())

    def getOptions(self):
        return list(self.shortOpts.values())


class CommandLine:
    def __init__(self, args=None, options=None, deprecatedHandler=None):
        self.args = list(args) if args is not None else []
        self.options = list(options) if options is not None else []
        self.deprecatedHandler = deprecatedHandler

    def addArg(self, arg):
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt):
        if opt is not None:
            self.options.append(opt)

    def getArgs(self):
        return list(self.args)

    def getArgList(self):
        return self.args

    def getOptions(self):
        return list(self.options)

    def _resolveOption(self, opt):
        actual = _Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt):
        if isinstance(opt, Option):
            return opt in self.options
        return self._resolveOption(opt) is not None

    def getOptionValue(self, opt, defaultValue=None):
        if isinstance(opt, Option):
            values = self.getOptionValues(opt)
            ans = values[0] if values else None
        else:
            resolved = self._resolveOption(opt)
            ans = self.getOptionValue(resolved) if resolved else None
        if ans is not None:
            return ans
        if callable(defaultValue):
            return defaultValue()
        return defaultValue

    def getOptionValues(self, opt):
        option = opt if isinstance(opt, Option) else self._resolveOption(opt)
        if option is None:
            return None
        values = []
        for processedOption in self.options:
            if processedOption == option:
                values.extend(processedOption.getValuesList())
        return list(values) if values else None


class DefaultParser:
    def __init__(self, allowPartialMatching=True, stripLeadingAndTrailingQuotes=None, deprecatedHandler=None):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = stripLeadingAndTrailingQuotes
        self.deprecatedHandler = deprecatedHandler
        self.cmd = None
        self.options = None
        self.stopAtNonOption = False
        self.currentToken = None
        self.currentOption = None
        self.skipParsing = False
        self.expectedOpts = None

    def parse(self, options, arguments, stopAtNonOption=False, properties=None):
        if isinstance(stopAtNonOption, dict) and properties is None:
            properties = stopAtNonOption
            stopAtNonOption = False

        self.options = options
        self.stopAtNonOption = stopAtNonOption
        self.skipParsing = False
        self.currentOption = None
        self.expectedOpts = list(options.getRequiredOptions())

        for group in options.getOptionGroups():
            group.setSelected(None)

        self.cmd = CommandLine(deprecatedHandler=self.deprecatedHandler)

        if arguments is not None:
            for argument in arguments:
                self._handleToken(argument)

        self._checkRequiredArgs()
        self._handleProperties(properties)
        self._checkRequiredOptions()
        return self.cmd

    def _checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self):
        if self.expectedOpts:
            raise MissingOptionException(self.expectedOpts)

    def _getLongPrefix(self, token):
        t = _Util.stripLeadingHyphens(token)
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
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _handleProperties(self, properties):
        if not properties:
            return
        for option, value in properties.items():
            opt = self.options.getOption(option)
            if opt is None:
                raise UnrecognizedOptionException("Default option wasn't defined", option)
            group = self.options.getOptionGroup(opt)
            selected = group is not None and group.isSelected()
            if not self.cmd.hasOption(option) and not selected:
                if opt.hasArg():
                    if not opt.getValues():
                        opt.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(str(value)))
                elif str(value).lower() not in ("yes", "true", "1"):
                    continue
                self._handleOption(opt)
                self.currentOption = None

    def _handleShortAndLongOption(self, hyphenToken):
        token = _Util.stripLeadingHyphens(hyphenToken)
        pos = token.find("=")
        if len(token) == 1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            else:
                self._handleUnknownToken(hyphenToken)
        elif pos == -1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            elif self._getMatchingLongOptions(token):
                self._handleLongOptionWithoutEqual(hyphenToken)
            else:
                opt = self._getLongPrefix(token)
                if opt is not None and self.options.getOption(opt).acceptsArg():
                    self._handleOption(self.options.getOption(opt))
                    self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[len(opt):]))
                    self.currentOption = None
                elif self._isJavaProperty(token):
                    self._handleOption(self.options.getOption(token[:1]))
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
                self._handleOption(self.options.getOption(opt[:1]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self._handleLongOptionWithEqual(hyphenToken)

    def _handleToken(self, token):
        if token is not None:
            self.currentToken = token
            if self.skipParsing:
                self.cmd.addArg(token)
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
            raise UnrecognizedOptionException("Unrecognized option: " + token, token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _isArgument(self, token):
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isJavaProperty(self, token):
        opt = token[:1] if token else None
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isLongOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        t = token if pos == -1 else token[:pos]
        if self._getMatchingLongOptions(t):
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isNegativeNumber(self, token):
        try:
            float(token)
            return True
        except (ValueError, TypeError):
            return False

    def _isOption(self, token):
        return self._isLongOption(token) or self._isShortOption(token)

    def _isShortOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
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
