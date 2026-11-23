import copy
from typing import List, Optional, Any, Union


class ParseException(Exception):
    def __init__(self, message: Optional[Union[str, Exception]] = None):
        if isinstance(message, Exception):
            super().__init__(str(message))
            self.cause = message
        else:
            super().__init__(message if message is not None else "")
            self.cause = None

    @classmethod
    def wrap(cls, e: Exception) -> 'ParseException':
        if isinstance(e, ParseException):
            return e
        return cls(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: List[str]):
        msg = f"Ambiguous option: '{option}'  (could be: "
        msg += ", ".join(f"'{m}'" for m in matchingOptions)
        msg += ")"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message: Union['Option', str]):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option = option_or_message
        else:
            super().__init__(option_or_message)
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_message: Union[List[Any], str]):
        if isinstance(missingOptions_or_message, list):
            missing = missingOptions_or_message
            msg = "Missing required option" + ("" if len(missing) == 1 else "s") + ": "
            msg += ", ".join(str(item) for item in missing)
            super().__init__(msg)
            self.missingOptions = list(missing)
        else:
            super().__init__(missingOptions_or_message)
            self.missingOptions = []

    def getMissingOptions(self) -> List[Any]:
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message: Union['OptionGroup', str], option: Optional['Option'] = None):
        if isinstance(group_or_message, OptionGroup):
            group = group_or_message
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(msg)
            self.group = group
            self.option = option
        else:
            super().__init__(group_or_message)
            self.group = None
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option

    def getOptionGroup(self) -> Optional['OptionGroup']:
        return self.group


class _Util:
    @staticmethod
    def isEmpty(s: Optional[str]) -> bool:
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingHyphens(s: Optional[str]) -> Optional[str]:
        if _Util.isEmpty(s):
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s: Optional[str]) -> Optional[str]:
        if _Util.isEmpty(s):
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
            return s[1:length - 1]
        return s


class _OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-')

    @staticmethod
    def _isJavaIdentifierPart(c: str) -> bool:
        return c.isalnum() or c in ('$', '_')

    @classmethod
    def isValidOpt(cls, c: str) -> bool:
        return cls._isJavaIdentifierPart(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def isValidChar(cls, c: str) -> bool:
        return cls._isJavaIdentifierPart(c) or c == '-'

    @classmethod
    def validate(cls, option: Optional[str]) -> Optional[str]:
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

    def __init__(self, option: Optional[str], longOption: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None):
        if isinstance(hasArg, str) and description is None:
            description = hasArg
            hasArg = False
            longOption = None
        elif isinstance(longOption, bool) and isinstance(hasArg, str) and description is None:
            description = hasArg
            hasArg = longOption
            longOption = None

        self.option = _OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.argName: Optional[str] = None
        self.required: bool = False
        self.optionalArg: bool = False
        self.values: List[str] = []
        self.valueSeparator: str = '\0'
        self.deprecated = None
        self.since: Optional[str] = None
        self.type = str
        self.converter = None

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self.longOption = longOpt

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def hasArg(self) -> bool:
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def getDescription(self) -> Optional[str]:
        return self.description

    def setDescription(self, description: Optional[str]) -> None:
        self.description = description

    def getArgName(self) -> Optional[str]:
        return self.argName

    def setArgName(self, argName: Optional[str]) -> None:
        self.argName = argName

    def hasArgName(self) -> bool:
        return self.argName is not None and len(self.argName) > 0

    def hasOptionalArg(self) -> bool:
        return self.optionalArg

    def setOptionalArg(self, optionalArg: bool) -> None:
        self.optionalArg = optionalArg

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int) -> None:
        self.argCount = num

    def getKey(self) -> Optional[str]:
        return self.longOption if self.option is None else self.option

    def getValue(self, index_or_default: Optional[Union[int, str]] = None) -> Optional[str]:
        if not self.values:
            if isinstance(index_or_default, str):
                return index_or_default
            return None
        if index_or_default is None:
            return self.values[0]
        if isinstance(index_or_default, int):
            return self.values[index_or_default]
        return self.values[0] if self.values else index_or_default

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if self.values else None

    def getValuesList(self) -> List[str]:
        return self.values

    def clearValues(self) -> None:
        self.values.clear()

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self) -> bool:
        if self.optionalArg:
            return False
        if self.argCount == self.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator != '\0' and len(self.valueSeparator) > 0

    def getValueSeparator(self) -> str:
        return self.valueSeparator

    def setValueSeparator(self, sep: str) -> None:
        self.valueSeparator = sep

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value: str) -> None:
        if self.argCount == self.UNINITIALIZED:
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

    def __str__(self) -> str:
        buf = ["[ Option ", str(self.option)]
        if self.longOption:
            buf.extend([" ", self.longOption])
        if self.hasArgs():
            buf.append("[ARG...]")
        elif self.hasArg():
            buf.append(" [ARG]")
        buf.extend([" :: ", str(self.description), " :: ", str(self.type), " ]"])
        return "".join(buf)


class OptionGroup:
    def __init__(self):
        self.optionMap: dict[str, Option] = {}
        self.selected: Optional[str] = None
        self.required: bool = False

    def addOption(self, option: Option) -> 'OptionGroup':
        self.optionMap[option.getKey()] = option
        return self

    def getNames(self) -> List[str]:
        return sorted(list(self.optionMap.keys()))

    def getOptions(self) -> List[Option]:
        return list(self.optionMap.values())

    def getSelected(self) -> Optional[str]:
        return self.selected

    def isSelected(self) -> bool:
        return self.selected is not None

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def setSelected(self, option: Optional[Option]) -> None:
        if option is None:
            self.selected = None
            return
        if self.selected is not None and self.selected != option.getKey():
            raise AlreadySelectedException(self, option)
        self.selected = option.getKey()

    def __str__(self) -> str:
        parts = []
        for opt in self.getOptions():
            if opt.getOpt() is not None:
                s = f"-{opt.getOpt()}"
            else:
                s = f"--{opt.getLongOpt()}"
            if opt.getDescription() is not None:
                s += f" {opt.getDescription()}"
            parts.append(s)
        return "[" + ", ".join(parts) + "]"


class Options:
    def __init__(self):
        self.shortOpts: dict[str, Option] = {}
        self.longOpts: dict[str, Option] = {}
        self.requiredOpts: List[Any] = []
        self.optionGroups: dict[str, OptionGroup] = {}

    def addOption(self, opt_or_str: Union[Option, str], *args: Any) -> 'Options':
        if isinstance(opt_or_str, Option):
            opt = opt_or_str
        else:
            if len(args) == 1:
                opt = Option(opt_or_str, args[0])
            elif len(args) == 2:
                opt = Option(opt_or_str, args[0], args[1])
            elif len(args) == 3:
                opt = Option(opt_or_str, args[0], args[1], args[2])
            else:
                raise ValueError("Invalid arguments to addOption")
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

    def hasOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def hasLongOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def getOption(self, opt: str) -> Optional[Option]:
        clean = _Util.stripLeadingHyphens(opt)
        return self.shortOpts.get(clean, self.longOpts.get(clean))

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> List[OptionGroup]:
        seen = set()
        res = []
        for g in self.optionGroups.values():
            if id(g) not in seen:
                seen.add(id(g))
                res.append(g)
        return res

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())

    def getRequiredOptions(self) -> List[Any]:
        return list(self.requiredOpts)

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matching = []
        for longOpt in self.longOpts.keys():
            if longOpt.startswith(clean):
                matching.append(longOpt)
        return matching


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

    def getArgList(self) -> List[str]:
        return self.args

    def getOptions(self) -> List[Option]:
        return list(self.options)

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = _Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Union[str, Option, OptionGroup]) -> bool:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        if isinstance(opt, Option):
            return opt in self.options
        return self.hasOption(self._resolveOption(opt))

    def getOptionValues(self, opt: Union[str, Option, OptionGroup]) -> Optional[List[str]]:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
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
        return values if values else None

    def getOptionValue(self, opt: Union[str, Option, OptionGroup], defaultValue: Optional[str] = None) -> Optional[str]:
        values = self.getOptionValues(opt)
        val = values[0] if values else None
        return val if val is not None else defaultValue


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes: Optional[bool] = None
        self.cmd: Optional[CommandLine] = None
        self.options: Optional[Options] = None
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: List[Any] = []

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

    def _checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self) -> None:
        if self.expectedOpts:
            raise MissingOptionException(self.expectedOpts)

    def _isJavaProperty(self, token: Optional[str]) -> bool:
        opt = None if (token is None or len(token) == 0) else token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token)
        return token

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                for item in list(self.expectedOpts):
                    if item is group:
                        self.expectedOpts.remove(item)
            group.setSelected(option)

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = _Util.stripLeadingHyphens(token)
        if t is None:
            return None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                return prefix
        return None

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
        if not matchingOpts:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleLongOptionWithEqual(self, token: str) -> None:
        pos = token.find('=')
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
        if '=' not in token:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = _Util.stripLeadingHyphens(hyphenToken)
        pos = token.find('=')
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

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    def _isShortOption(self, token: str) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _isLongOption(self, token: str) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        t = token if pos == -1 else token[:pos]
        if len(self._getMatchingLongOptions(t)) > 0:
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isOption(self, token: str) -> bool:
        return self._isLongOption(token) or self._isShortOption(token)

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _handleToken(self, token: Optional[str]) -> None:
        if token is None:
            return
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
