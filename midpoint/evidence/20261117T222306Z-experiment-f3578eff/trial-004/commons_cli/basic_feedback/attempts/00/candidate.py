import copy
from typing import List, Optional, Any

class ParseException(Exception):
    def __init__(self, message_or_cause=""):
        super().__init__(str(message_or_cause))
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e: Exception) -> 'ParseException':
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: List[str]):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{m}'" for m in matchingOptions) + ")"
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
    def __init__(self, missingOptions):
        if isinstance(missingOptions, list):
            count = len(missingOptions)
            s = "" if count == 1 else "s"
            msg = f"Missing required option{s}: " + ", ".join(str(m) for m in missingOptions)
            super().__init__(msg)
            self.missingOptions = list(missingOptions)
        else:
            super().__init__(str(missingOptions))
            self.missingOptions = []

    def getMissingOptions(self) -> list:
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg, option=None):
        if option is not None:
            super().__init__(f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_msg.getSelected()}'")
            self.group = group_or_msg
            self.option = option
        else:
            super().__init__(str(group_or_msg))
            self.group = None
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option

    def getOptionGroup(self) -> Any:
        return self.group


def _is_java_identifier_part(c: str) -> bool:
    if not c:
        return False
    return c.isalnum() or c in ('_', '$')


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-',)

    @staticmethod
    def _isValidOpt(c: str) -> bool:
        return _is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def _isValidChar(c: str) -> bool:
        return _is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_LONG_CHARS

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
    def stripLeadingHyphens(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:-1].find('"') == -1:
            return s[1:-1]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option: Optional[str], longOption_or_hasArg: Any, hasArg: Optional[bool] = None, description: Optional[str] = None):
        # Handling overloaded constructor shapes
        # Signature 1: Option(opt: str?, longOpt: str?, hasArg: bool, desc: str?)
        # Signature 2: Option(opt: str, hasArg: bool, desc: str)
        # Contract: Option(string, string, bool, string)
        if isinstance(longOption_or_hasArg, str) or (longOption_or_hasArg is None and hasArg is not None):
            longOption = longOption_or_hasArg
            has_arg = bool(hasArg)
            desc = description
        elif isinstance(longOption_or_hasArg, bool):
            longOption = None
            has_arg = longOption_or_hasArg
            desc = hasArg
        else:
            longOption = str(longOption_or_hasArg) if longOption_or_hasArg is not None else None
            has_arg = bool(hasArg) if hasArg is not None else False
            desc = description

        self.option = OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if has_arg else self.UNINITIALIZED
        self.description = desc
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.values: List[str] = []
        self.valueSeparator: str = '\0'
        self.deprecated = None
        self.since = None

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self.longOption = longOpt

    def getKey(self) -> Optional[str]:
        return self.longOption if self.option is None else self.option

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

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int) -> None:
        self.argCount = num

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def getValueSeparator(self) -> str:
        return self.valueSeparator

    def setValueSeparator(self, sep: str) -> None:
        self.valueSeparator = sep

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

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
        if self.hasValueSeparator():
            sep = self.getValueSeparator()
            index = add_val.find(sep)
            while index != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add_val[:index])
                add_val = add_val[index + 1:]
                index = add_val.find(sep)
        self._add(add_val)

    def getValue(self, index_or_default: Any = None) -> Optional[str]:
        if isinstance(index_or_default, int):
            if len(self.values) == 0 or index_or_default < 0 or index_or_default >= len(self.values):
                return None
            return self.values[index_or_default]
        if isinstance(index_or_default, str):
            val = self.getValue()
            return val if val is not None else index_or_default
        return None if len(self.values) == 0 else self.values[0]

    def getValues(self) -> Optional[List[str]]:
        return None if len(self.values) == 0 else list(self.values)

    def getValuesList(self) -> List[str]:
        return self.values

    def clearValues(self) -> None:
        self.values.clear()

    def clone(self) -> 'Option':
        opt = copy.copy(self)
        opt.values = list(self.values)
        return opt

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self) -> int:
        return hash((self.longOption, self.option))


class OptionGroup:
    def __init__(self):
        self.optionMap: dict = {}
        self.selected: Optional[str] = None
        self.required: bool = False

    def addOption(self, option: Option) -> 'OptionGroup':
        self.optionMap[option.getKey()] = option
        return self

    def getNames(self) -> list:
        return list(self.optionMap.keys())

    def getOptions(self) -> list:
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
        self.shortOpts: dict = {}
        self.longOpts: dict = {}
        self.requiredOpts: list = []
        self.optionGroups: dict = {}

    def addOption(self, opt: Option) -> 'Options':
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

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> list:
        seen = set()
        res = []
        for g in self.optionGroups.values():
            if id(g) not in seen:
                seen.add(id(g))
                res.append(g)
        return res

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        return [l for l in self.longOpts.keys() if l.startswith(clean)]

    def getOption(self, opt: str) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        return self.shortOpts.get(clean, self.longOpts.get(clean))

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())

    def getRequiredOptions(self) -> List[Any]:
        return list(self.requiredOpts)

    def hasLongOption(self, opt: str) -> bool:
        return Util.stripLeadingHyphens(opt) in self.longOpts

    def hasOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt: str) -> bool:
        return Util.stripLeadingHyphens(opt) in self.shortOpts


class CommandLine:
    def __init__(self, args: Optional[List[str]] = None, options: Optional[List[Option]] = None):
        self.args: List[str] = list(args) if args is not None else []
        self.options: List[Option] = list(options) if options is not None else []

    def addArg(self, arg: Optional[str]) -> None:
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt: Optional[Option]) -> None:
        if opt is not None:
            self.options.append(opt)

    def getArgs(self) -> List[str]:
        return list(self.args)

    def _resolveOption(self, opt: str) -> Optional[Option]:
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Any) -> bool:
        if isinstance(opt, Option):
            return opt in self.options
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        return self.hasOption(self._resolveOption(opt))

    def getOptionValue(self, opt: Any, defaultValue: Optional[str] = None) -> Optional[str]:
        if isinstance(opt, Option):
            values = self.getOptionValues(opt)
            ans = values[0] if values is not None and len(values) > 0 else None
            return ans if ans is not None else defaultValue
        if isinstance(opt, OptionGroup):
            values = self.getOptionValues(opt)
            ans = values[0] if values is not None and len(values) > 0 else None
            return ans if ans is not None else defaultValue
        return self.getOptionValue(self._resolveOption(opt), defaultValue)

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
        if isinstance(opt, Option):
            values = []
            for processed in self.options:
                if processed == opt:
                    values.extend(processed.getValuesList())
            return values if len(values) > 0 else None
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        return self.getOptionValues(self._resolveOption(opt))


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self.allowPartialMatching: bool = allowPartialMatching
        self.stripLeadingAndTrailingQuotes: Optional[bool] = None
        self.cmd: CommandLine = CommandLine()
        self.options: Optional[Options] = None
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: list = []

    def _indexOfEqual(self, token: str) -> int:
        return token.find('=')

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.stripLeadingHyphens(token)
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                return prefix
        return None

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            opt = self.options.getOption(token)
            if opt and opt.getLongOpt():
                matches.append(opt.getLongOpt())
        return matches

    def _checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self) -> None:
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())
        if self.options.getOptionGroup(option) is not None:
            group = self.options.getOptionGroup(option)
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _handleUnknownToken(self, token: str) -> None:
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

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
        if len(matchingOpts) == 0:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleLongOptionWithEqual(self, token: str) -> None:
        pos = self._indexOfEqual(token)
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

    def _handleLongOption(self, token: str) -> None:
        if self._indexOfEqual(token) == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = self._indexOfEqual(token)
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

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isJavaProperty(self, token: Optional[str]) -> bool:
        if not token:
            return False
        opt = token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self._indexOfEqual(token)
        t = token if pos == -1 else token[:pos]
        if len(self._getMatchingLongOptions(t)) > 0:
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    def _isOption(self, token: str) -> bool:
        return self._isLongOption(token) or self._isShortOption(token)

    def _isShortOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self._indexOfEqual(token)
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

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
            for argument in arguments:
                self._handleToken(argument)
        self._checkRequiredArgs()
        self._checkRequiredOptions()
        return self.cmd
