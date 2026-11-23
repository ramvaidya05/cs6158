from typing import List, Optional, Any
import copy


class ParseException(Exception):
    def __init__(self, message_or_cause: Any = None):
        if isinstance(message_or_cause, Exception):
            super().__init__(str(message_or_cause))
            self.__cause__ = message_or_cause
        else:
            super().__init__(str(message_or_cause) if message_or_cause is not None else None)

    @staticmethod
    def wrap(e: BaseException) -> "ParseException":
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
    def __init__(self, option: str, matchingOptions: List[str]):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{o}'" for o in matchingOptions) + ")"
        super().__init__(msg, option)
        self._matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return list(self._matchingOptions)


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message: Any):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self._option: Optional[Option] = option_or_message
        else:
            super().__init__(str(option_or_message))
            self._option = None

    def getOption(self) -> Optional["Option"]:
        return self._option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_message: Any):
        if isinstance(missingOptions_or_message, list):
            s = "s" if len(missingOptions_or_message) != 1 else ""
            msg = f"Missing required option{s}: " + ", ".join(str(o) for o in missingOptions_or_message)
            super().__init__(msg)
            self._missingOptions: Optional[List[Any]] = list(missingOptions_or_message)
        else:
            super().__init__(str(missingOptions_or_message))
            self._missingOptions = None

    def getMissingOptions(self) -> Optional[List[Any]]:
        return self._missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message: Any, option: Optional["Option"] = None):
        if isinstance(group_or_message, OptionGroup) and option is not None:
            super().__init__(
                f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group_or_message.getSelected()}'"
            )
            self._group: Optional[OptionGroup] = group_or_message
            self._option: Optional[Option] = option
        else:
            super().__init__(str(group_or_message))
            self._group = None
            self._option = None

    def getOption(self) -> Optional["Option"]:
        return self._option

    def getOptionGroup(self) -> Optional["OptionGroup"]:
        return self._group


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-',)

    @staticmethod
    def isValidOpt(c: str) -> bool:
        return c.isalnum() or c in ('_', '$') or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def isValidChar(c: str) -> bool:
        return c.isalnum() or c in ('_', '$') or c in OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def validate(option: Optional[str]) -> Optional[str]:
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


class Util:
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


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option: Optional[str], longOption: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None):
        self._option = OptionValidator.validate(option)
        self._longOption = longOption
        self._argCount = 1 if hasArg else Option.UNINITIALIZED
        self._description = description
        self._required = False
        self._optionalArg = False
        self._argName: Optional[str] = None
        self._values: List[str] = []
        self._valueSeparator: int = 0

    def getOpt(self) -> Optional[str]:
        return self._option

    def getLongOpt(self) -> Optional[str]:
        return self._longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self._longOption = longOpt

    def getKey(self) -> Optional[str]:
        return self._longOption if self._option is None else self._option

    def hasArg(self) -> bool:
        return self._argCount > 0 or self._argCount == Option.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self._argCount > 1 or self._argCount == Option.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self._required

    def setRequired(self, required: bool) -> None:
        self._required = required

    def getValue(self) -> Optional[str]:
        return self._values[0] if self._values else None

    def getValues(self) -> Optional[List[str]]:
        return list(self._values) if self._values else None

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
        self._optionalArg = optionalArg

    def getArgs(self) -> int:
        return self._argCount

    def setArgs(self, num: int) -> None:
        self._argCount = num

    def hasValueSeparator(self) -> bool:
        return self._valueSeparator > 0

    def getValueSeparator(self) -> int:
        return self._valueSeparator

    def setValueSeparator(self, sep: str) -> None:
        self._valueSeparator = ord(sep) if sep else 0

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self._argCount <= 0 or len(self._values) < self._argCount)

    def requiresArg(self) -> bool:
        if self._optionalArg:
            return False
        if self._argCount == Option.UNLIMITED_VALUES:
            return len(self._values) == 0
        return self.acceptsArg()

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self._values.append(value)

    def processValue(self, value: str) -> None:
        if self._argCount == Option.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = value
        if self.hasValueSeparator():
            sep = chr(self._valueSeparator)
            index = add.find(sep)
            while index != -1:
                if len(self._values) == self._argCount - 1:
                    break
                self._add(add[:index])
                add = add[index + 1:]
                index = add.find(sep)
        self._add(add)

    def clearValues(self) -> None:
        self._values.clear()

    def clone(self) -> "Option":
        opt = copy.copy(self)
        opt._values = list(self._values)
        return opt

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

    def __str__(self) -> str:
        buf = ["[ Option ", self._option or ""]
        if self._longOption:
            buf.extend([" ", self._longOption])
        if self.hasArgs():
            buf.append("[ARG...]")
        elif self.hasArg():
            buf.append(" [ARG]")
        buf.extend([" :: ", self._description or "", " ]"]
        return "".join(buf)


class OptionGroup:
    def __init__(self):
        self._optionMap: dict[str, Option] = {}
        self._selected: Optional[str] = None
        self._required: bool = False

    def addOption(self, option: Option) -> "OptionGroup":
        key = option.getKey()
        if key is not None:
            self._optionMap[key] = option
        return self

    def getNames(self) -> List[str]:
        return sorted(list(self._optionMap.keys()))

    def getOptions(self) -> List[Option]:
        return list(self._optionMap.values())

    def getSelected(self) -> Optional[str]:
        return self._selected

    def isRequired(self) -> bool:
        return self._required

    def isSelected(self) -> bool:
        return self._selected is not None

    def setRequired(self, required: bool) -> None:
        self._required = required

    def setSelected(self, option: Optional[Option]) -> None:
        if option is None:
            self._selected = None
            return
        key = option.getKey()
        if self._selected is not None and self._selected != key:
            raise AlreadySelectedException(self, option)
        self._selected = key

    def __str__(self) -> str:
        parts = []
        for opt in self.getOptions():
            if opt.getOpt() is not None:
                s = f"-{opt.getOpt()}"
            else:
                s = f"--{opt.getLongOpt()}"
            if opt.getDescription() is not None:
                s = f"{s} {opt.getDescription()}"
            parts.append(s)
        return "[" + ", ".join(parts) + "]"


class Options:
    def __init__(self):
        self._shortOpts: dict[str, Option] = {}
        self._longOpts: dict[str, Option] = {}
        self._requiredOpts: list[Any] = []
        self._optionGroups: dict[str, OptionGroup] = {}

    def addOption(self, opt: Option) -> "Options":
        key = opt.getKey()
        if opt.hasLongOpt():
            self._longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self._requiredOpts:
                self._requiredOpts.remove(key)
            self._requiredOpts.append(key)
        if key is not None:
            self._shortOpts[key] = opt
        return self

    def addOptionGroup(self, group: OptionGroup) -> "Options":
        if group.isRequired():
            self._requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            key = option.getKey()
            if key is not None:
                self._optionGroups[key] = group
        return self

    def hasOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return (clean in self._shortOpts) or (clean in self._longOpts)

    def hasLongOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self._longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self._shortOpts

    def getOption(self, opt: Optional[str]) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        res = self._shortOpts.get(clean)
        return res if res is not None else self._longOpts.get(clean)

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        key = opt.getKey()
        return self._optionGroups.get(key) if key is not None else None

    def getOptionGroups(self) -> List[OptionGroup]:
        # Unique set preserving order
        seen = set()
        res = []
        for g in self._optionGroups.values():
            if id(g) not in seen:
                seen.add(id(g))
                res.append(g)
        return res

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self._longOpts:
            return [clean]
        return [longOpt for longOpt in self._longOpts if longOpt.startswith(clean)]

    def getRequiredOptions(self) -> List[Any]:
        return list(self._requiredOpts)

    def getOptions(self) -> List[Option]:
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

    def _resolveOption(self, opt: str) -> Optional[Option]:
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self._options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Any) -> bool:
        if opt is None:
            return False
        if isinstance(opt, Option):
            return opt in self._options
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        # String
        resolved = self._resolveOption(str(opt))
        if resolved is not None:
            return resolved in self._options
        return False

    def getOptionValue(self, opt: Any, defaultValue: Optional[str] = None) -> Optional[str]:
        values = self.getOptionValues(opt)
        val = values[0] if values else None
        return val if val is not None else defaultValue

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
        if opt is None:
            return None
        if isinstance(opt, Option):
            target = opt
            values: List[str] = []
            for processedOption in self._options:
                if processedOption == target:
                    values.extend(processedOption.getValuesList())
            return list(values) if values else None
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            selected = opt.getSelected()
            return self.getOptionValues(selected) if selected is not None else None
        # String
        resolved = self._resolveOption(str(opt))
        if resolved is None:
            return None
        return self.getOptionValues(resolved)

    def getOptions(self) -> List[Option]:
        return list(self._options)


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self._allowPartialMatching = allowPartialMatching
        self._stripLeadingAndTrailingQuotes: Optional[bool] = None
        self.cmd: Optional[CommandLine] = None
        self.options: Optional[Options] = None
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: List[Any] = []

    def _checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            key = self.currentOption.getKey()
            if self._isJavaProperty(key) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self) -> None:
        if self.expectedOpts:
            raise MissingOptionException(self.expectedOpts)

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.stripLeadingHyphens(token) or ""
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                return prefix
        return None

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self._allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            opt = self.options.getOption(token)
            if opt and opt.getLongOpt():
                matches.append(opt.getLongOpt())
        return matches

    def _stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self._stripLeadingAndTrailingQuotes is not None and self._stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token) or token
        return token

    def _stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self._stripLeadingAndTrailingQuotes is None or self._stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token) or token
        return token

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            key = option.getKey()
            if key in self.expectedOpts:
                self.expectedOpts.remove(key)
        group = self.options.getOptionGroup(option)
        if group is not None:
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
        token = Util.stripLeadingHyphens(hyphenToken) or ""
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

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isJavaProperty(self, token: Optional[str]) -> bool:
        opt = token[:1] if (token is not None and len(token) > 0) else None
        option = self.options.getOption(opt) if opt is not None else None
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

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
        pos = token.find("=")
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _handleToken(self, token: Optional[str]) -> None:
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

    def parse(self, options: Options, arguments: List[str], stopAtNonOption: bool = False) -> CommandLine:
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
