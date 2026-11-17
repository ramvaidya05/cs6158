import copy
import math


class ParseException(Exception):
    def __init__(self, message_or_cause=""):
        if isinstance(message_or_cause, BaseException):
            super().__init__(str(message_or_cause))
            self.__cause__ = message_or_cause
        else:
            super().__init__(str(message_or_cause))

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


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message):
        if isinstance(option_or_message, Option):
            super().__init__("Missing argument for option: " + str(option_or_message.getKey()))
            self.option = option_or_message
        else:
            super().__init__(str(option_or_message))
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_options_or_message):
        if isinstance(missing_options_or_message, list):
            msg = MissingOptionException._createMessage(missing_options_or_message)
            super().__init__(msg)
            self.missingOptions = list(missing_options_or_message)
        else:
            super().__init__(str(missing_options_or_message))
            self.missingOptions = None

    @staticmethod
    def _createMessage(missing_options):
        buf = ["Missing required option", "" if len(missing_options) == 1 else "s", ": "]
        it = iter(missing_options)
        first = True
        for opt in it:
            if not first:
                buf.append(", ")
            buf.append(str(opt))
            first = False
        return "".join(buf)

    def getMissingOptions(self):
        return self.missingOptions


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matching_options):
        msg = AmbiguousOptionException._createMessage(option, matching_options)
        super().__init__(msg, option)
        self.matchingOptions = list(matching_options)

    @staticmethod
    def _createMessage(option, matching_options):
        buf = ["Ambiguous option: '", str(option), "'  (could be: "]
        first = True
        for opt in matching_options:
            if not first:
                buf.append(", ")
            buf.append("'")
            buf.append(str(opt))
            buf.append("'")
            first = False
        buf.append(")")
        return "".join(buf)

    def getMatchingOptions(self):
        return self.matchingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message, option=None):
        if option is not None:
            super().__init__(
                f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_message.getSelected()}'"
            )
            self.group = group_or_message
            self.option = option
        else:
            super().__init__(str(group_or_message))
            self.group = None
            self.option = None

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group


class _OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def _is_java_identifier_part(c):
        return c.isalnum() or c in ('$', '_')

    @classmethod
    def _is_valid_char(cls, c):
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_LONG_CHARS

    @classmethod
    def _is_valid_opt(cls, c):
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def validate(cls, option):
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not cls._is_valid_opt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not cls._is_valid_char(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class _Util:
    @staticmethod
    def isEmpty(s):
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingHyphens(s):
        if _Util.isEmpty(s):
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s):
        if _Util.isEmpty(s):
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
            return s[1:length - 1]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option, longOption=None, hasArg=False, description=None):
        # Support both constructor overloads and direct contract signature
        if isinstance(hasArg, str) and description is None:
            # Option(option, description)
            description = hasArg
            hasArg = False
            longOption = None
        elif isinstance(longOption, bool) and description is None:
            # Option(option, hasArg, description)
            description = hasArg
            hasArg = longOption
            longOption = None

        self.deprecated = None
        self.option = _OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else Option.UNINITIALIZED
        self.description = description
        self.argName = None
        self.optionalArg = False
        self.required = False
        self.since = None
        self.type = str
        self.values = []
        self.valueSeparator = '\0'
        self.converter = None

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def hasArg(self):
        return self.argCount > 0 or self.argCount == Option.UNLIMITED_VALUES

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == Option.UNLIMITED_VALUES

    def hasOptionalArg(self):
        return self.optionalArg

    def hasLongOpt(self):
        return self.longOption is not None

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = bool(required)

    def isDeprecated(self):
        return self.deprecated is not None

    def getKey(self):
        return self.longOption if self.option is None else self.option

    def getArgs(self):
        return self.argCount

    def setArgs(self, num):
        self.argCount = num

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    def getArgName(self):
        return self.argName

    def setArgName(self, argName):
        self.argName = argName

    def getValueSeparator(self):
        return self.valueSeparator

    def setValueSeparator(self, sep):
        self.valueSeparator = sep

    def hasValueSeparator(self):
        return self.valueSeparator != '\0' and len(self.valueSeparator) > 0

    def getValue(self, default_or_index=None):
        if default_or_index is None:
            return None if len(self.values) == 0 else self.values[0]
        if isinstance(default_or_index, int):
            if len(self.values) == 0:
                return None
            return self.values[default_or_index]
        val = self.getValue()
        return val if val is not None else default_or_index

    def getValues(self):
        return None if len(self.values) == 0 else list(self.values)

    def getValuesList(self):
        return self.values

    def clearValues(self):
        self.values.clear()

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
                add = add[index + len(sep):]
                index = add.find(sep)
        self._add(add)

    def clone(self):
        cp = copy.copy(self)
        cp.values = list(self.values)
        return cp

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
        buf.append(f" :: {self.description} :: {self.type} ]")
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
        return list(self.optionMap.keys())

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
            if option.getOpt() is not None:
                buf.append(f"-{option.getOpt()}")
            else:
                buf.append(f"--{option.getLongOpt()}")
            if option.getDescription() is not None:
                buf.append(f" {option.getDescription()}")
            first = False
        buf.append("]")
        return "".join(buf)


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt, longOpt=None, hasArg=False, description=None):
        if isinstance(opt, Option):
            option = opt
        else:
            option = Option(opt, longOpt, hasArg, description)

        key = option.getKey()
        if option.hasLongOpt():
            self.longOpts[option.getLongOpt()] = option
        if option.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = option
        return self

    def addOptionGroup(self, group):
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
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
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getOptionGroup(self, opt):
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        seen = set()
        res = []
        for g in self.optionGroups.values():
            if g not in seen:
                seen.add(g)
                res.append(g)
        return res

    def getOptions(self):
        return list(self.shortOpts.values())

    def getRequiredOptions(self):
        res = []
        for item in self.requiredOpts:
            if isinstance(item, OptionGroup):
                res.append(str(item))
            else:
                res.append(str(item))
        return res

    def getMatchingOptions(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matches = []
        for longOpt in self.longOpts.keys():
            if longOpt.startswith(clean):
                matches.append(longOpt)
        return matches


class CommandLine:
    def __init__(self, args=None, options=None):
        self.args = [] if args is None else list(args)
        self.options = [] if options is None else list(options)

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

    def hasOption(self, opt):
        if isinstance(opt, Option):
            return opt in self.options
        return self._resolveOption(opt) is not None

    def _resolveOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        if clean is not None:
            for option in self.options:
                if clean == option.getOpt() or clean == option.getLongOpt():
                    return option
        return None

    def getOptionValue(self, opt, defaultValue=None):
        if isinstance(opt, Option):
            values = self.getOptionValues(opt)
            if values is not None and len(values) > 0:
                return values[0]
            return defaultValue() if callable(defaultValue) else defaultValue
        resolved = self._resolveOption(opt)
        return self.getOptionValue(resolved, defaultValue)

    def getOptionValues(self, opt):
        if isinstance(opt, Option):
            values = []
            for processed in self.options:
                if processed == opt:
                    values.extend(processed.getValuesList())
            return values if len(values) > 0 else None
        resolved = self._resolveOption(opt)
        return self.getOptionValues(resolved) if resolved is not None else None


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
            for arg in arguments:
                self._handleToken(arg)

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
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def _handleProperties(self, properties):
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
                    if opt.getValues() is None or len(opt.getValues()) == 0:
                        opt.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(value))
                elif str(value).lower() not in ("yes", "true", "1"):
                    continue
                self._handleOption(opt)
                self.currentOption = None

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _handleOption(self, option):
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _updateRequiredOptions(self, option):
        if option.isRequired():
            key = option.getKey()
            if key in self.expectedOpts:
                self.expectedOpts.remove(key)

        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                g_str = str(group)
                if g_str in self.expectedOpts:
                    self.expectedOpts.remove(g_str)
                elif group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)

    def _getMatchingLongOptions(self, token):
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def _getLongPrefix(self, token):
        t = _Util.stripLeadingHyphens(token)
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def _isJavaProperty(self, token):
        opt = None if len(token) == 0 else token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isNegativeNumber(self, token):
        try:
            float(token)
            return True
        except ValueError:
            return False

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

    def _isOption(self, token):
        return self._isLongOption(token) or self._isShortOption(token)

    def _isArgument(self, token):
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _handleUnknownToken(self, token):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException("Unrecognized option: " + token, token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

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

    def _handleLongOptionWithoutEqual(self, token):
        matchingOpts = self._getMatchingLongOptions(token)
        if len(matchingOpts) == 0:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleLongOptionWithEqual(self, token):
        pos = token.find("=")
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self._getMatchingLongOptions(opt)
        if len(matchingOpts) == 0:
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

    def _handleLongOption(self, token):
        if token.find("=") == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

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
            elif len(self._getMatchingLongOptions(token)) > 0:
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
