import copy
from typing import List, Optional, Any

class ParseException(Exception):
    def __init__(self, message_or_cause=None):
        super().__init__(str(message_or_cause) if message_or_cause is not None else "")
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e: Exception) -> 'ParseException':
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg, option=None):
        if option is not None:
            super().__init__(f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_msg.getSelected()}'")
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


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{o}'" for o in matchingOptions) + ")"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, option_or_msg):
        if isinstance(option_or_msg, Option):
            super().__init__(f"Missing argument for option: {option_or_msg.getKey()}")
            self.option = option_or_msg
        else:
            super().__init__(str(option_or_msg))
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_msg):
        if isinstance(missingOptions_or_msg, list):
            msg = "Missing required option" + ("" if len(missingOptions_or_msg) == 1 else "s") + ": " + ", ".join(str(o) for o in missingOptions_or_msg)
            super().__init__(msg)
            self.missingOptions = list(missingOptions_or_msg)
        else:
            super().__init__(str(missingOptions_or_msg))
            self.missingOptions = []

    def getMissingOptions(self) -> list:
        return self.missingOptions


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def _is_java_identifier_part(c: str) -> bool:
        return c.isalnum() or c in ('$', '_')

    @classmethod
    def _isValidChar(cls, c: str) -> bool:
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_LONG_CHARS

    @classmethod
    def _isValidOpt(cls, c: str) -> bool:
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def validate(cls, option: Optional[str]) -> Optional[str]:
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not cls._isValidOpt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not cls._isValidChar(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class Util:
    @staticmethod
    def stripLeadingAndTrailingQuotes(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and '"' not in s[1:-1]:
            return s[1:-1]
        return s

    @staticmethod
    def stripLeadingHyphens(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, opt: Optional[str], longOpt: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None):
        if isinstance(longOpt, bool) and description is None:
            description = hasArg
            hasArg = longOpt
            longOpt = None

        self.option = OptionValidator.validate(opt)
        self.longOption = longOpt
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.values: List[str] = []
        self.valueSeparator: Optional[str] = None
        self.type = str
        self.converter = None
        self.deprecated = None
        self.since = None

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def hasArg(self) -> bool:
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def hasOptionalArg(self) -> bool:
        return self.optionalArg

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = bool(required)

    def getValue(self, default_or_index: Any = None) -> Optional[str]:
        if isinstance(default_or_index, int):
            if not self.values or default_or_index < 0 or default_or_index >= len(self.values):
                raise IndexError(f"Index {default_or_index} out of bounds")
            return self.values[default_or_index]
        if not self.values:
            return default_or_index
        return self.values[0]

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if self.values else None

    def getValuesList(self) -> List[str]:
        return self.values

    def getKey(self) -> str:
        return self.option if self.option is not None else self.longOption

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self) -> bool:
        if self.optionalArg:
            return False
        if self.argCount == self.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value: str) -> None:
        if self.argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add_val = value
        if self.valueSeparator:
            sep = self.valueSeparator
            idx = add_val.find(sep)
            while idx != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add_val[:idx])
                add_val = add_val[idx + 1:]
                idx = add_val.find(sep)
        self._add(add_val)

    def clearValues(self) -> None:
        self.values.clear()

    def clone(self) -> 'Option':
        opt = copy.copy(self)
        opt.values = list(self.values)
        return opt

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int) -> None:
        self.argCount = num

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self) -> int:
        return hash((self.longOption, self.option))


class OptionGroup:
    def __init__(self):
        self.optionMap = {}
        self.selected = None
        self.required = False

    def addOption(self, option: Option) -> 'OptionGroup':
        self.optionMap[option.getKey()] = option
        return self

    def getNames(self):
        return list(self.optionMap.keys())

    def getOptions(self):
        return list(self.optionMap.values())

    def getSelected(self) -> Optional[str]:
        return self.selected

    def isRequired(self) -> bool:
        return self.required

    def isSelected(self) -> bool:
        return self.selected is not None

    def setRequired(self, required: bool) -> None:
        self.required = bool(required)

    def setSelected(self, option: Optional[Option]) -> None:
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

    def addOption(self, opt_or_option: Any, longOpt: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None) -> 'Options':
        if isinstance(opt_or_option, Option):
            opt = opt_or_option
        else:
            opt = Option(opt_or_option, longOpt, hasArg, description)
        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def addOptionGroup(self, group: OptionGroup) -> 'Options':
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
        return self

    def hasOption(self, opt: Optional[str]) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasLongOption(self, opt: Optional[str]) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def hasShortOption(self, opt: Optional[str]) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def getOption(self, opt: Optional[str]) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getMatchingOptions(self, opt: Optional[str]) -> List[str]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        return [longOpt for longOpt in self.longOpts.keys() if longOpt.startswith(clean)]

    def getRequiredOptions(self) -> List[Any]:
        return list(self.requiredOpts)

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        return list(set(self.optionGroups.values()))

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())


class CommandLine:
    def __init__(self, args: Optional[List[str]] = None, options: Optional[List[Option]] = None):
        self.args = list(args) if args is not None else []
        self.options = list(options) if options is not None else []

    def addArg(self, arg: Optional[str]) -> None:
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt: Optional[Option]) -> None:
        if opt is not None:
            self.options.append(opt)

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Any) -> bool:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        if isinstance(opt, Option):
            return opt in self.options
        return self._resolveOption(opt) is not None

    def getOptionValue(self, opt: Any, defaultValue: Optional[str] = None) -> Optional[str]:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return defaultValue
            return self.getOptionValue(opt.getSelected(), defaultValue)
        if isinstance(opt, Option):
            values = self.getOptionValues(opt)
            if values:
                return values[0]
            return defaultValue
        resolved = self._resolveOption(opt)
        if resolved is not None:
            return self.getOptionValue(resolved, defaultValue)
        return defaultValue

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        if isinstance(opt, Option):
            res: List[str] = []
            for processed in self.options:
                if processed == opt:
                    res.extend(processed.getValuesList())
            return res if res else None
        resolved = self._resolveOption(opt)
        if resolved is not None:
            return self.getOptionValues(resolved)
        return None

    def getArgs(self) -> List[str]:
        return list(self.args)

    def getOptions(self) -> List[Option]:
        return list(self.options)


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = None
        self.cmd: Optional[CommandLine] = None
        self.options: Optional[Options] = None
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: List[Any] = []

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.stripLeadingHyphens(token)
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                return prefix
        return None

    def _isJavaProperty(self, token: str) -> bool:
        opt = token[:1] if token else None
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    def _isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        t = token if pos == -1 else token[:pos]
        if len(self._getMatchingLongOptions(t)) > 0:
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isShortOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _isOption(self, token: str) -> bool:
        return self._isLongOption(token) or self._isShortOption(token)

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self) -> None:
        if self.expectedOpts:
            raise MissingOptionException(self.expectedOpts)

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        opt_copy = option.clone()
        self._updateRequiredOptions(opt_copy)
        self.cmd.addOption(opt_copy)
        self.currentOption = opt_copy if opt_copy.hasArg() else None

    def _handleUnknownToken(self, token: str) -> None:
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _handleConcatenatedOptions(self, token: str) -> None:
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self._handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            self._handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def _handleLongOptionWithoutEqual(self, token: str) -> None:
        matchingOpts = self._getMatchingLongOptions(token)
        if not matchingOpts:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleLongOptionWithEqual(self, token: str) -> None:
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

    def _handleLongOption(self, token: str) -> None:
        if token.find("=") == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
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

    def _handleToken(self, token: str) -> None:
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

    def parse(self, options: Options, arguments: Optional[List[str]], stopAtNonOption: bool = False) -> CommandLine:
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
        self._checkRequiredOptions()
        return self.cmd
