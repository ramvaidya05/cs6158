from typing import List, Optional, Any, Dict
import copy


class ParseException(Exception):
    pass


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


class AlreadySelectedException(ParseException):
    def __init__(self, message_or_group: Any, option: Optional['Option'] = None):
        if isinstance(message_or_group, OptionGroup):
            group = message_or_group
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(msg)
            self.group = group
            self.option = option
        else:
            super().__init__(str(message_or_group))
            self.group = None
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option

    def getOptionGroup(self) -> Optional['OptionGroup']:
        return self.group


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: List[str]):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{m}'" for m in matchingOptions) + ")"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, message_or_option: Any):
        if isinstance(message_or_option, Option):
            super().__init__(f"Missing argument for option: {message_or_option.getKey()}")
            self.option = message_or_option
        else:
            super().__init__(str(message_or_option))
            self.option = None

    def getOption(self) -> Optional['Option']:
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_msg: Any):
        if isinstance(missingOptions_or_msg, list):
            missing = missingOptions_or_msg
            s = "s" if len(missing) != 1 else ""
            msg = f"Missing required option{s}: " + ", ".join(str(o) for o in missing)
            super().__init__(msg)
            self.missingOptions = list(missing)
        else:
            super().__init__(str(missingOptions_or_msg))
            self.missingOptions = []

    def getMissingOptions(self) -> List[Any]:
        return self.missingOptions


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def isValidOpt(c: str) -> boolean if False else bool:
        return (c.isalnum() or c in ('$', '_')) or (c in OptionValidator.ADDITIONAL_OPTION_CHARS)

    @staticmethod
    def isValidChar(c: str) -> bool:
        return (c.isalnum() or c in ('$', '_')) or (c in OptionValidator.ADDITIONAL_LONG_CHARS)

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


class Util:
    @staticmethod
    def isEmpty(s: Optional[str]) -> bool:
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingHyphens(str_: Optional[str]) -> Optional[str]:
        if Util.isEmpty(str_):
            return str_
        if str_.startswith("--"):
            return str_[2:]
        if str_.startswith("-"):
            return str_[1:]
        return str_

    @staticmethod
    def stripLeadingAndTrailingQuotes(str_: Optional[str]) -> Optional[str]:
        if Util.isEmpty(str_):
            return str_
        length = len(str_)
        if length > 1 and str_.startswith('"') and str_.endswith('"') and ('"' not in str_[1:length - 1]):
            return str_[1:length - 1]
        return str_


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option: Optional[str], longOption_or_hasArg: Any = None, hasArg_or_desc: Any = None, description: Optional[str] = None):
        if description is None and isinstance(hasArg_or_desc, str) and isinstance(longOption_or_hasArg, bool):
            opt = option
            longOpt = None
            has_arg = longOption_or_hasArg
            desc = hasArg_or_desc
        elif description is None and isinstance(longOption_or_hasArg, str) and hasArg_or_desc is None:
            opt = option
            longOpt = None
            has_arg = False
            desc = longOption_or_hasArg
        else:
            opt = option
            longOpt = longOption_or_hasArg
            has_arg = bool(hasArg_or_desc)
            desc = description

        self.option = OptionValidator.validate(opt)
        self.longOption = longOpt
        self.argCount = 1 if has_arg else self.UNINITIALIZED
        self.description = desc
        self.argName: Optional[str] = None
        self.required = False
        self.optionalArg = False
        self.values: List[str] = []
        self.valueSeparator: Optional[str] = None

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self.longOption = longOpt

    def getKey(self) -> Optional[str]:
        return self.option if self.option is not None else self.longOption

    def hasArg(self) -> bool:
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def getValue(self, index: Optional[int] = None) -> Optional[str]:
        if not self.values:
            return None
        if index is None:
            return self.values[0]
        return self.values[index]

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if self.values else None

    def getValuesList(self) -> List[str]:
        return self.values

    def getDescription(self) -> Optional[str]:
        return self.description

    def setDescription(self, description: Optional[str]) -> None:
        self.description = description

    def getArgName(self) -> Optional[str]:
        return self.argName

    def setArgName(self, argName: Optional[str]) -> None:
        self.argName = argName

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def hasOptionalArg(self) -> bool:
        return self.optionalArg

    def setOptionalArg(self, optionalArg: bool) -> None:
        self.optionalArg = optionalArg

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int) -> None:
        self.argCount = num

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self) -> bool:
        if self.optionalArg:
            return False
        if self.argCount == self.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def hasArgs(self) -> bool:
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator is not None and len(self.valueSeparator) > 0

    def setValueSeparator(self, sep: str) -> None:
        self.valueSeparator = sep

    def getValueSeparator(self) -> Optional[str]:
        return self.valueSeparator

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value: str) -> None:
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

    def clearValues(self) -> None:
        self.values.clear()

    def clone(self) -> 'Option':
        c = copy.copy(self)
        c.values = list(self.values)
        return c

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self) -> int:
        return hash((self.longOption, self.option))

    def __repr__(self) -> str:
        return self.getKey() or ""


class OptionGroup:
    def __init__(self):
        self.optionMap: Dict[str, Option] = {}
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

    def isRequired(self) -> bool:
        return self.required

    def isSelected(self) -> bool:
        return self.selected is not None

    def setRequired(self, required: bool) -> None:
        self.required = required

    def setSelected(self, option: Optional[Option]) -> None:
        if option is None:
            self.selected = None
            return
        if self.selected is not None and self.selected != option.getKey():
            raise AlreadySelectedException(self, option)
        self.selected = option.getKey()

    def __repr__(self) -> str:
        res = []
        for opt in self.getOptions():
            if opt.getOpt() is not None:
                res.append("-" + opt.getOpt() + (f" {opt.getDescription()}" if opt.getDescription() else ""))
            else:
                res.append("--" + str(opt.getLongOpt()) + (f" {opt.getDescription()}" if opt.getDescription() else ""))
        return "[" + ", ".join(res) + "]"


class Options:
    def __init__(self):
        self.shortOpts: Dict[str, Option] = {}
        self.longOpts: Dict[str, Option] = {}
        self.requiredOpts: List[Any] = []
        self.optionGroups: Dict[str, OptionGroup] = {}

    def addOption(self, opt_or_str: Any, longOpt: Any = None, hasArg: bool = False, description: Optional[str] = None) -> 'Options':
        if isinstance(opt_or_str, Option):
            opt = opt_or_str
        else:
            if longOpt is None and not hasArg and description is None:
                opt = Option(opt_or_str, False, None)
            elif isinstance(longOpt, bool):
                opt = Option(opt_or_str, longOpt, hasArg if isinstance(hasArg, str) else description)
            elif isinstance(longOpt, str) and isinstance(hasArg, str):
                opt = Option(opt_or_str, False, longOpt)
            else:
                opt = Option(opt_or_str, longOpt, hasArg, description)

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
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def hasLongOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def getOption(self, opt: str) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

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
        clean = Util.stripLeadingHyphens(opt)
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
        return self.hasOption(self._resolveOption(opt))

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
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

    def getOptionValue(self, opt: Any, defaultValue: Optional[str] = None) -> Optional[str]:
        values = self.getOptionValues(opt)
        res = values[0] if values else None
        return res if res is not None else defaultValue


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

    @staticmethod
    def indexOfEqual(token: str) -> int:
        return token.find('=')

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
            if opt.getLongOpt():
                matches.append(opt.getLongOpt())
        return matches

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

    def _handleLongOption(self, token: str) -> None:
        if self.indexOfEqual(token) == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleLongOptionWithEqual(self, token: str) -> None:
        pos = self.indexOfEqual(token)
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

    def _handleLongOptionWithoutEqual(self, token: str) -> None:
        matchingOpts = self._getMatchingLongOptions(token)
        if not matchingOpts:
            self._handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self._handleOption(self.options.getOption(key))

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = self.indexOfEqual(token)
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

    def _handleUnknownToken(self, token: str) -> None:
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

    def _isJavaProperty(self, token: Optional[str]) -> bool:
        if token is None or len(token) == 0:
            return False
        opt = token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self.indexOfEqual(token)
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
        pos = self.indexOfEqual(token)
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

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired() and option.getKey() in self.expectedOpts:
            self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)
