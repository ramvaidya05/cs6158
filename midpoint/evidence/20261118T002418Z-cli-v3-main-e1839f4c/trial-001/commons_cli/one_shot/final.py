from __future__ import annotations
import copy
from typing import Any, Collection, Iterator, List, Optional, Sequence, Union


class ParseException(Exception):
    def __init__(self, message: Union[str, Exception] = ""):
        super().__init__(str(message))

    @staticmethod
    def wrap(e: Exception) -> ParseException:
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self._option = option

    def getOption(self) -> Optional[str]:
        return self._option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: Collection[str]):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{m}'" for m in matchingOptions) + ")"
        super().__init__(msg, option)
        self._matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return list(self._matchingOptions)


class MissingArgumentException(ParseException):
    def __init__(self, option: Union[Option, str]):
        if isinstance(option, Option):
            super().__init__(f"Missing argument for option: {option.getKey()}")
            self._option: Optional[Option] = option
        else:
            super().__init__(str(option))
            self._option = None

    def getOption(self) -> Optional[Option]:
        return self._option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions: Union[List[Any], str]):
        if isinstance(missingOptions, list):
            msg = "Missing required option" + ("" if len(missingOptions) == 1 else "s") + ": " + ", ".join(str(o) for o in missingOptions)
            super().__init__(msg)
            self._missingOptions: Optional[List[Any]] = list(missingOptions)
        else:
            super().__init__(str(missingOptions))
            self._missingOptions = None

    def getMissingOptions(self) -> Optional[List[Any]]:
        return self._missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg: Union[OptionGroup, str], option: Optional[Option] = None):
        if isinstance(group_or_msg, OptionGroup) and option is not None:
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_msg.getSelected()}'"
            super().__init__(msg)
            self._group: Optional[OptionGroup] = group_or_msg
            self._option: Optional[Option] = option
        else:
            super().__init__(str(group_or_msg))
            self._group = None
            self._option = None

    def getOption(self) -> Optional[Option]:
        return self._option

    def getOptionGroup(self) -> Optional[OptionGroup]:
        return self._group


class _Util:
    @staticmethod
    def isEmpty(s: Optional[str]) -> bool:
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingHyphens(s: Optional[str]) -> Optional[str]:
        if s is None or len(s) == 0:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s: Optional[str]) -> Optional[str]:
        if s is None or len(s) == 0:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
            return s[1:length - 1]
        return s


class _OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @classmethod
    def _is_java_id_part(cls, c: str) -> bool:
        return c.isalnum() or c in ('$', '_')

    @classmethod
    def isValidOpt(cls, c: str) -> bool:
        return cls._is_java_id_part(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def isValidChar(cls, c: str) -> bool:
        return cls._is_java_id_part(c) or c in cls.ADDITIONAL_LONG_CHARS

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
        self._option = _OptionValidator.validate(option)
        self._longOption = longOption
        self._argCount = 1 if hasArg else self.UNINITIALIZED
        self._description = description
        self._required = False
        self._optionalArg = False
        self._argName: Optional[str] = None
        self._values: List[str] = []
        self._valueSeparator: str = '\0'

    def getOpt(self) -> Optional[str]:
        return self._option

    def getLongOpt(self) -> Optional[str]:
        return self._longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self._longOption = longOpt

    def getKey(self) -> Optional[str]:
        return self._longOption if self._option is None else self._option

    def hasArg(self) -> bool:
        return self._argCount > 0 or self._argCount == self.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self._argCount > 1 or self._argCount == self.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self._required

    def setRequired(self, required: bool) -> None:
        self._required = bool(required)

    def getValue(self, index_or_default: Any = None) -> Optional[str]:
        if isinstance(index_or_default, int):
            if not self._values:
                return None
            return self._values[index_or_default]
        if isinstance(index_or_default, str):
            val = self.getValue()
            return val if val is not None else index_or_default
        return None if not self._values else self._values[0]

    def getValues(self) -> Optional[List[str]]:
        return None if not self._values else list(self._values)

    def getValuesList(self) -> List[str]:
        return self._values

    def getDescription(self) -> Optional[str]:
        return self._description

    def setDescription(self, description: Optional[str]) -> None:
        self._description = description

    def getArgName(self) -> Optional[str]:
        return self._argName

    def setArgName(self, argName: Optional[str]) -> None:
        self._argName = argName

    def hasLongOpt(self) -> bool:
        return self._longOption is not None

    def hasOptionalArg(self) -> bool:
        return self._optionalArg

    def setOptionalArg(self, optionalArg: bool) -> None:
        self._optionalArg = bool(optionalArg)

    def getArgs(self) -> int:
        return self._argCount

    def setArgs(self, num: int) -> None:
        self._argCount = int(num)

    def hasValueSeparator(self) -> bool:
        return ord(self._valueSeparator) > 0

    def getValueSeparator(self) -> str:
        return self._valueSeparator

    def setValueSeparator(self, sep: str) -> None:
        self._valueSeparator = sep

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self._argCount <= 0 or len(self._values) < self._argCount)

    def requiresArg(self) -> bool:
        if self._optionalArg:
            return False
        if self._argCount == self.UNLIMITED_VALUES:
            return len(self._values) == 0
        return self.acceptsArg()

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self._values.append(value)

    def processValue(self, value: str) -> None:
        if self._argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add_str = value
        if self.hasValueSeparator():
            sep = self._valueSeparator
            index = add_str.find(sep)
            while index != -1:
                if len(self._values) == self._argCount - 1:
                    break
                self._add(add_str[:index])
                add_str = add_str[index + 1:]
                index = add_str.find(sep)
        self._add(add_str)

    def clearValues(self) -> None:
        self._values.clear()

    def clone(self) -> Option:
        c = copy.copy(self)
        c._values = list(self._values)
        return c

    def isDeprecated(self) -> bool:
        return False

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self._longOption == other._longOption and self._option == other._option

    def __hash__(self) -> int:
        return hash((self._longOption, self._option))


class OptionGroup:
    def __init__(self):
        self._optionMap: dict[str, Option] = {}
        self._selected: Optional[str] = None
        self._required: bool = False

    def addOption(self, option: Option) -> OptionGroup:
        self._optionMap[option.getKey()] = option
        return self

    def getNames(self) -> List[str]:
        return sorted(list(self._optionMap.keys()))

    def getOptions(self) -> Collection[Option]:
        return self._optionMap.values()

    def getSelected(self) -> Optional[str]:
        return self._selected

    def isRequired(self) -> bool:
        return self._required

    def isSelected(self) -> bool:
        return self._selected is not None

    def setRequired(self, required: bool) -> None:
        self._required = bool(required)

    def setSelected(self, option: Optional[Option]) -> None:
        if option is None:
            self._selected = None
            return
        if self._selected is not None and self._selected != option.getKey():
            raise AlreadySelectedException(self, option)
        self._selected = option.getKey()


class Options:
    def __init__(self):
        self._shortOpts: dict[str, Option] = {}
        self._longOpts: dict[str, Option] = {}
        self._requiredOpts: list[Any] = []
        self._optionGroups: dict[str, OptionGroup] = {}

    def addOption(self, opt_or_str: Union[Option, str], *args: Any) -> Options:
        if isinstance(opt_or_str, Option):
            opt = opt_or_str
            key = opt.getKey()
            if opt.hasLongOpt():
                self._longOpts[opt.getLongOpt()] = opt
            if opt.isRequired():
                if key in self._requiredOpts:
                    self._requiredOpts.remove(key)
                self._requiredOpts.append(key)
            self._shortOpts[key] = opt
            return self
        else:
            if len(args) == 1:
                return self.addOption(Option(opt_or_str, None, False, args[0]))
            elif len(args) == 2:
                return self.addOption(Option(opt_or_str, None, args[0], args[1]))
            elif len(args) == 3:
                return self.addOption(Option(opt_or_str, args[0], args[1], args[2]))
            raise ValueError("Invalid arguments for addOption")

    def addOptionGroup(self, group: OptionGroup) -> Options:
        if group.isRequired():
            self._requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self._optionGroups[option.getKey()] = group
        return self

    def hasOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self._shortOpts or clean in self._longOpts

    def hasLongOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self._longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self._shortOpts

    def getOption(self, opt: Optional[str]) -> Optional[Option]:
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self._shortOpts:
            return self._shortOpts[clean]
        return self._longOpts.get(clean)

    def getRequiredOptions(self) -> List[Any]:
        return list(self._requiredOpts)

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self._longOpts:
            return [clean]
        matching = []
        for longOpt in self._longOpts:
            if longOpt.startswith(clean):
                matching.append(longOpt)
        return matching

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self._optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> Collection[OptionGroup]:
        seen = set()
        res = []
        for og in self._optionGroups.values():
            if id(og) not in seen:
                seen.add(id(og))
                res.append(og)
        return res

    def getOptions(self) -> Collection[Option]:
        return list(self._shortOpts.values())


class CommandLine:
    def __init__(self, args: Optional[List[str]] = None, options: Optional[List[Option]] = None):
        self._args: List[str] = list(args) if args is not None else []
        self._options: List[Option] = list(options) if options is not None else []

    def addArg(self, arg: Optional[str]) -> None:
        if arg is not None:
            self._args.append(arg)

    def addOption(self, opt: Optional[Option]) -> None:
        if opt is not None:
            self._options.append(opt)

    def getArgs(self) -> List[str]:
        return list(self._args)

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = _Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self._options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Union[str, Option, OptionGroup]) -> bool:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        if isinstance(opt, Option):
            return opt in self._options
        return self._resolveOption(opt) is not None

    def getOptionValues(self, opt: Union[str, Option, OptionGroup]) -> Optional[List[str]]:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        option = opt if isinstance(opt, Option) else self._resolveOption(opt)
        if option is None:
            return None
        values = []
        for processedOption in self._options:
            if processedOption == option:
                values.extend(processedOption.getValuesList())
        return values if len(values) > 0 else None

    def getOptionValue(self, opt: Union[str, Option, OptionGroup], defaultValue: Optional[str] = None) -> Optional[str]:
        values = self.getOptionValues(opt)
        if values is not None and len(values) > 0:
            return values[0]
        return defaultValue


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self._allowPartialMatching = bool(allowPartialMatching)
        self._stripLeadingAndTrailingQuotes: Optional[bool] = None
        self.cmd: CommandLine = CommandLine()
        self.options: Options = Options()
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: List[Any] = []

    def parse(self, options: Options, arguments: Optional[Sequence[str]], stopAtNonOption: bool = False) -> CommandLine:
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
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def _isJavaProperty(self, token: Optional[str]) -> bool:
        opt = None if not token else token[0:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = _Util.stripLeadingHyphens(token) or ""
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self._allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            opt = self.options.getOption(token)
            if opt is not None and opt.getLongOpt() is not None:
                matches.append(opt.getLongOpt())
        return matches

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired() and option.getKey() in self.expectedOpts:
            self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)

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

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    def _isOption(self, token: str) -> bool:
        return self._isLongOption(token) or self._isShortOption(token)

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

    def _handleUnknownToken(self, token: str) -> None:
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _handleLongOption(self, token: str) -> None:
        if "=" not in token:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

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

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = _Util.stripLeadingHyphens(hyphenToken) or ""
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
                    self._handleOption(self.options.getOption(token[0]))
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
                self._handleOption(self.options.getOption(opt[0]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self._handleLongOptionWithEqual(hyphenToken)

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

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self._stripLeadingAndTrailingQuotes is not None and self._stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token) or ""
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self._stripLeadingAndTrailingQuotes is None or self._stripLeadingAndTrailingQuotes:
            return _Util.stripLeadingAndTrailingQuotes(token) or ""
        return token
