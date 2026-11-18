import copy
import math

class ParseException(Exception):
    def __init__(self, message=None, cause=None):
        super().__init__(message if message is not None else str(cause) if cause is not None else "")
        self.cause = cause

    @staticmethod
    def wrap(e):
        if isinstance(e, ParseException):
            return e
        return ParseException(cause=e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matchingOptions):
        matching_str = ", ".join(f"'{opt}'" for opt in matchingOptions)
        message = f"Ambiguous option: '{option}'  (could be: {matching_str})"
        super().__init__(message, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self):
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option = option_or_message
        else:
            super().__init__(option_or_message)
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_options_or_message):
        if isinstance(missing_options_or_message, list):
            missing = missing_options_or_message
            s = "Missing required option" + ("" if len(missing) == 1 else "s") + ": " + ", ".join(str(o) for o in missing)
            super().__init__(s)
            self.missingOptions = list(missing)
        else:
            super().__init__(missing_options_or_message)
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message, option=None):
        if option is not None:
            group = group_or_message
            message = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(message)
            self.group = group
            self.option = option
        else:
            super().__init__(group_or_message)
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
    def is_java_identifier_start(c):
        return c.isalpha() or c in ('$', '_')

    @classmethod
    def is_java_identifier_part(cls, c):
        return cls.is_java_identifier_start(c) or c.isdigit()

    @classmethod
    def is_valid_opt(cls, c):
        return cls.is_java_identifier_part(c) or (c in cls.ADDITIONAL_OPTION_CHARS)

    @classmethod
    def is_valid_char(cls, c):
        return cls.is_java_identifier_part(c) or (c in cls.ADDITIONAL_LONG_CHARS)

    @classmethod
    def validate(cls, option):
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not cls.is_valid_opt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not cls.is_valid_char(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class _Util:
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
        if isinstance(option, str) or option is None:
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
            self.deprecated = None
            self.since = None
            self.converter = None
        else:
            raise ValueError("Invalid argument")

    def acceptsArg(self):
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self):
        if self.optionalArg:
            return False
        if self.argCount == self.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def _add(self, value):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value):
        if self.argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = value
        if self.hasValueSeparator():
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

    def getArgName(self):
        return self.argName

    def setArgName(self, argName):
        self.argName = argName

    def getArgs(self):
        return self.argCount

    def setArgs(self, num):
        self.argCount = num

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    def getKey(self):
        return self.longOption if self.option is None else self.option

    def getLongOpt(self):
        return self.longOption

    def setLongOpt(self, longOpt):
        self.longOption = longOpt

    def getOpt(self):
        return self.option

    def getValue(self, index_or_default=None):
        if index_or_default is None:
            return self.values[0] if self.values else None
        if isinstance(index_or_default, int):
            return self.values[index_or_default] if self.values else None
        val = self.getValue()
        return val if val is not None else index_or_default

    def getValues(self):
        return list(self.values) if self.values else None

    def getValuesList(self):
        return self.values

    def getValueSeparator(self):
        return self.valueSeparator

    def setValueSeparator(self, sep):
        self.valueSeparator = sep

    def hasArg(self):
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def hasArgName(self):
        return bool(self.argName)

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def hasLongOpt(self):
        return self.longOption is not None

    def hasOptionalArg(self):
        return self.optionalArg

    def setOptionalArg(self, optionalArg):
        self.optionalArg = optionalArg

    def hasValueSeparator(self):
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def isDeprecated(self):
        return self.deprecated is not None

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = required


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
        self.required = required

    def setSelected(self, option):
        if option is None:
            self.selected = None
            return
        if self.selected is not None and self.selected != option.getKey():
            raise AlreadySelectedException(self, option)
        self.selected = option.getKey()


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt_or_opt_str, *args):
        if isinstance(opt_or_opt_str, Option):
            opt = opt_or_opt_str
        else:
            opt_str = opt_or_opt_str
            if len(args) == 1:
                opt = Option(opt_str, False, args[0])
            elif len(args) == 2:
                opt = Option(opt_str, args[0], args[1])
            elif len(args) == 3:
                opt = Option(opt_str, args[0], args[1], args[2])
            else:
                raise ValueError("Invalid arguments")
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

    def addOptions(self, options):
        for opt in options.getOptions():
            if self.hasOption(opt.getKey()):
                raise ValueError(f"Duplicate key: {opt.getKey()}")
            self.addOption(opt)
        for grp in options.getOptionGroups():
            self.addOptionGroup(grp)
        return self

    def addRequiredOption(self, opt, longOpt, hasArg, description):
        option = Option(opt, longOpt, hasArg, description)
        option.setRequired(True)
        self.addOption(option)
        return self

    def getMatchingOptions(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matching = []
        for longOpt in self.longOpts.keys():
            if longOpt.startswith(clean):
                matching.append(longOpt)
        return matching

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
        for grp in self.optionGroups.values():
            if id(grp) not in seen:
                seen.add(id(grp))
                res.append(grp)
        return res

    def getOptions(self):
        return list(self.shortOpts.values())

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def hasLongOption(self, opt):
        return _Util.stripLeadingHyphens(opt) in self.longOpts

    def hasOption(self, opt):
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt):
        return _Util.stripLeadingHyphens(opt) in self.shortOpts


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
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        if isinstance(opt, Option):
            return opt in self.options
        return self.hasOption(self._resolveOption(opt))

    def getOptionValues(self, opt):
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        if isinstance(opt, str):
            return self.getOptionValues(self._resolveOption(opt))
        if opt is None:
            return None
        values = []
        for processedOption in self.options:
            if processedOption == opt:
                values.extend(processedOption.getValuesList())
        return list(values) if len(values) > 0 else None

    def getOptionValue(self, opt, defaultValue=None):
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return defaultValue() if callable(defaultValue) else defaultValue
            return self.getOptionValue(opt.getSelected(), defaultValue)
        if isinstance(opt, str):
            return self.getOptionValue(self._resolveOption(opt), defaultValue)
        values = self.getOptionValues(opt)
        answer = values[0] if values is not None else None
        if answer is not None:
            return answer
        return defaultValue() if callable(defaultValue) else defaultValue


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

    def _checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self):
        if len(self.expectedOpts) > 0:
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
        pos = token.index("=")
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

    def _handleLongOptionWithoutEqual(self, token):
        matchingOpts = self._getMatchingLongOptions(token)
        if len(matchingOpts) == 0:
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

    def _handleUnknownToken(self, token):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _isArgument(self, token):
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isJavaProperty(self, token):
        opt = None if len(token) == 0 else token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

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

    def _isNegativeNumber(self, token):
        try:
            float(token)
            return token.startswith("-")
        except ValueError:
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
                self._handleToken(argument)
        self._checkRequiredArgs()
        self._checkRequiredOptions()
        return self.cmd

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
