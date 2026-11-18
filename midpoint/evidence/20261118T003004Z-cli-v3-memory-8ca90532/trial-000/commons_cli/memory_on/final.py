from __future__ import annotations
import copy
from typing import Any, List, Optional, Set, Dict


class ParseException(Exception):
    def __init__(self, message: Any = None) -> None:
        super().__init__(str(message) if message is not None else "")

    @staticmethod
    def wrap(e: Exception) -> ParseException:
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None) -> None:
        super().__init__(message)
        self._option = option

    def getOption(self) -> Optional[str]:
        return self._option


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg: Any, option: Optional[Option] = None) -> None:
        if isinstance(group_or_msg, OptionGroup) and option is not None:
            group = group_or_msg
            super().__init__(
                f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            )
            self._group = group
            self._option = option
        else:
            super().__init__(str(group_or_msg))
            self._group = None
            self._option = None

    def getOption(self) -> Optional[Option]:
        return self._option

    def getOptionGroup(self) -> Optional[OptionGroup]:
        return self._group


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: List[str]) -> None:
        buf = f"Ambiguous option: '{option}'  (could be: "
        buf += ", ".join(f"'{m}'" for m in matchingOptions)
        buf += ")"
        super().__init__(buf, option)
        self._matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return self._matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, opt_or_msg: Any) -> None:
        if isinstance(opt_or_msg, Option):
            super().__init__(f"Missing argument for option: {opt_or_msg.getKey()}")
            self._option = opt_or_msg
        else:
            super().__init__(str(opt_or_msg))
            self._option = None

    def getOption(self) -> Optional[Option]:
        return self._option


class MissingOptionException(ParseException):
    def __init__(self, missing_or_msg: Any) -> None:
        if isinstance(missing_or_msg, list):
            buf = "Missing required option" + ("" if len(missing_or_msg) == 1 else "s") + ": "
            buf += ", ".join(str(m) for m in missing_or_msg)
            super().__init__(buf)
            self._missingOptions = list(missing_or_msg)
        else:
            super().__init__(str(missing_or_msg))
            self._missingOptions = []

    def getMissingOptions(self) -> List[Any]:
        return self._missingOptions


class Util:
    @staticmethod
    def isEmpty(s: Optional[str]) -> bool:
        return s is None or len(s) == 0

    @staticmethod
    def stripLeadingHyphens(s: Optional[str]) -> Optional[str]:
        if Util.isEmpty(s) or s is None:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def stripLeadingAndTrailingQuotes(s: Optional[str]) -> Optional[str]:
        if Util.isEmpty(s) or s is None:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:length - 1].find('"') == -1:
            return s[1:length - 1]
        return s


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = ('?', '@')
    ADDITIONAL_LONG_CHARS = ('-',)

    @staticmethod
    def isValidOpt(c: str) -> bool:
        return (c.isalnum() or c in ('$', '_')) or (c in OptionValidator.ADDITIONAL_OPTION_CHARS)

    @staticmethod
    def isValidChar(c: str) -> bool:
        return (c.isalnum() or c in ('$', '_')) or (c in OptionValidator.ADDITIONAL_LONG_CHARS)

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


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option: Optional[str], longOption: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None) -> None:
        if isinstance(longOption, bool) and description is None:
            # (opt, hasArg, desc) format
            description = hasArg  # type: ignore
            hasArg = longOption
            longOption = None

        self._option = OptionValidator.validate(option)
        self._longOption = longOption
        self._argCount = 1 if hasArg else self.UNINITIALIZED
        self._description = description
        self._required = False
        self._optionalArg = False
        self._argName: Optional[str] = None
        self._values: List[str] = []
        self._valueSeparator = 0
        self._type = str
        self._converter = None
        self._deprecated = None
        self._since: Optional[str] = None

    def getOpt(self) -> Optional[str]:
        return self._option

    def getLongOpt(self) -> Optional[str]:
        return self._longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self._longOption = longOpt

    def getKey(self) -> Optional[str]:
        return self._option if self._option is not None else self._longOption

    def hasArg(self) -> bool:
        return self._argCount > 0 or self._argCount == self.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self._required

    def setRequired(self, required: bool) -> None:
        self._required = required

    def getValue(self, index_or_default: Any = None) -> Optional[str]:
        if index_or_default is None:
            return None if len(self._values) == 0 else self._values[0]
        if isinstance(index_or_default, int):
            return None if len(self._values) == 0 else self._values[index_or_default]
        # default string
        val = self.getValue()
        return val if val is not None else index_or_default

    def getValues(self) -> Optional[List[str]]:
        return None if len(self._values) == 0 else list(self._values)

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

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (
            self._argCount <= 0 or len(self._values) < self._argCount
        )

    def requiresArg(self) -> bool:
        if self._optionalArg:
            return False
        if self._argCount == self.UNLIMITED_VALUES:
            return len(self._values) == 0
        return self.acceptsArg()

    def hasArgs(self) -> bool:
        return self._argCount > 1 or self._argCount == self.UNLIMITED_VALUES

    def hasValueSeparator(self) -> bool:
        return self._valueSeparator > 0

    def isDeprecated(self) -> bool:
        return self._deprecated is not None

    def _add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self._values.append(value)

    def processValue(self, value: str) -> None:
        if self._argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add_val = value
        if self.hasValueSeparator():
            sep = chr(self._valueSeparator)
            idx = add_val.find(sep)
            while idx != -1:
                if len(self._values) == self._argCount - 1:
                    break
                self._add(add_val[:idx])
                add_val = add_val[idx + 1:]
                idx = add_val.find(sep)
        self._add(add_val)

    def clearValues(self) -> None:
        self._values.clear()

    def __copy__(self) -> Option:
        opt = Option(self._option, self._longOption, False, self._description)
        opt._argCount = self._argCount
        opt._required = self._required
        opt._optionalArg = self._optionalArg
        opt._argName = self._argName
        opt._values = list(self._values)
        opt._valueSeparator = self._valueSeparator
        opt._type = self._type
        opt._converter = self._converter
        opt._deprecated = self._deprecated
        opt._since = self._since
        return opt

    def clone(self) -> Option:
        return copy.copy(self)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self._longOption == other._longOption and self._option == other._option

    def __hash__(self) -> int:
        return hash((self._longOption, self._option))

    def __str__(self) -> str:
        return f"[ Option {self._option} {self._longOption} :: {self._description} ]"


class OptionGroup:
    def __init__(self) -> None:
        self._optionMap: Dict[str, Option] = {}
        self._selected: Optional[str] = None
        self._required: bool = False

    def addOption(self, option: Option) -> OptionGroup:
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

    def isSelected(self) -> bool:
        return self._selected is not None

    def isRequired(self) -> bool:
        return self._required

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
        res = ["["]
        items = []
        for opt in self.getOptions():
            s = f"-{opt.getOpt()}" if opt.getOpt() is not None else f"--{opt.getLongOpt()}"
            if opt.getDescription():
                s += f" {opt.getDescription()}"
            items.append(s)
        res.append(", ".join(items))
        res.append("]")
        return "".join(res)


class Options:
    def __init__(self) -> None:
        self._shortOpts: Dict[str, Option] = {}
        self._longOpts: Dict[str, Option] = {}
        self._requiredOpts: List[Any] = []
        self._optionGroups: Dict[str, OptionGroup] = {}

    def addOption(self, opt: Option) -> Options:
        key = opt.getKey()
        if opt.hasLongOpt():
            self._longOpts[opt.getLongOpt()] = opt  # type: ignore
        if opt.isRequired():
            if key in self._requiredOpts:
                self._requiredOpts.remove(key)
            self._requiredOpts.append(key)
        if key is not None:
            self._shortOpts[key] = opt
        return self

    def addOptionGroup(self, group: OptionGroup) -> Options:
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
        return clean in self._shortOpts or clean in self._longOpts

    def hasLongOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self._longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = Util.stripLeadingHyphens(opt)
        return clean in self._shortOpts

    def getOption(self, opt: Optional[str]) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        option = self._shortOpts.get(clean)  # type: ignore
        return option if option is not None else self._longOpts.get(clean)  # type: ignore

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        key = opt.getKey()
        return self._optionGroups.get(key) if key is not None else None

    def getOptionGroups(self) -> List[OptionGroup]:
        seen = set()
        res = []
        for g in self._optionGroups.values():
            if id(g) not in seen:
                seen.add(id(g))
                res.append(g)
        return res

    def getOptions(self) -> List[Option]:
        return list(self._shortOpts.values())

    def getRequiredOptions(self) -> List[Any]:
        return list(self._requiredOpts)

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = Util.stripLeadingHyphens(opt)
        if clean is None:
            return []
        if clean in self._longOpts:
            return [clean]
        return [longOpt for longOpt in self._longOpts if longOpt.startswith(clean)]


class CommandLine:
    def __init__(self, args: List[str], options: List[Option]) -> None:
        self._args = list(args)
        self._options = list(options)

    def getArgs(self) -> List[str]:
        return list(self._args)

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self._options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Any) -> bool:
        if isinstance(opt, Option):
            return opt in self._options
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        return self._resolveOption(opt) is not None

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
        if opt is None:
            return None
        if isinstance(opt, Option):
            values = []
            for processed in self._options:
                if processed == opt:
                    values.extend(processed.getValuesList())
            return values if len(values) > 0 else None
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        return self.getOptionValues(self._resolveOption(opt))

    def getOptionValue(self, opt: Any) -> Optional[str]:
        values = self.getOptionValues(opt)
        return None if values is None or len(values) == 0 else values[0]


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True) -> None:
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = None
        self.cmd: CommandLine = None  # type: ignore
        self.options: Options = None  # type: ignore
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

        raw_args: List[str] = []
        processed_options: List[Option] = []
        self._raw_args = raw_args
        self._processed_options = processed_options
        self.cmd = CommandLine(raw_args, processed_options)

        if arguments is not None:
            for argument in arguments:
                self.handleToken(argument)

        self.checkRequiredArgs()
        self.checkRequiredOptions()
        return CommandLine(self._raw_args, self._processed_options)

    def checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self.isJavaProperty(self.currentOption.getKey() or "") and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def checkRequiredOptions(self) -> None:
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.stripLeadingHyphens(token)
        if t is None:
            return None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                return prefix
        return None

    def getMatchingLongOptions(self, token: str) -> List[str]:
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            opt = self.options.getOption(token)
            if opt and opt.getLongOpt():
                matches.append(opt.getLongOpt())
        return matches

    def handleConcatenatedOptions(self, token: str) -> None:
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self.handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            opt = self.options.getOption(ch)
            if opt is not None:
                self.handleOption(opt)
                if self.currentOption is not None and len(token) != i + 1:
                    self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                    break

    def handleLongOption(self, token: str) -> None:
        pos = token.find("=")
        if pos == -1:
            self.handleLongOptionWithoutEqual(token)
        else:
            self.handleLongOptionWithEqual(token)

    def handleLongOptionWithEqual(self, token: str) -> None:
        pos = token.find("=")
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self.getMatchingLongOptions(opt)
        if len(matchingOpts) == 0:
            self.handleUnknownToken(self.currentToken or token)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matchingOpts)
        else:
            key = opt if self.options.hasLongOption(opt) else matchingOpts[0]
            option = self.options.getOption(key)
            if option and option.acceptsArg():
                self.handleOption(option)
                if self.currentOption is not None:
                    self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(value))
                    self.currentOption = None
            else:
                self.handleUnknownToken(self.currentToken or token)

    def handleLongOptionWithoutEqual(self, token: str) -> None:
        matchingOpts = self.getMatchingLongOptions(token)
        if len(matchingOpts) == 0:
            self.handleUnknownToken(self.currentToken or token)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            opt = self.options.getOption(key)
            if opt is not None:
                self.handleOption(opt)

    def handleOption(self, option: Option) -> None:
        self.checkRequiredArgs()
        copy_opt = option.clone()
        self.updateRequiredOptions(copy_opt)
        self._processed_options.append(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = Util.stripLeadingHyphens(hyphenToken) or ""
        pos = token.find("=")
        if len(token) == 1:
            if self.options.hasShortOption(token):
                opt = self.options.getOption(token)
                if opt is not None:
                    self.handleOption(opt)
            else:
                self.handleUnknownToken(hyphenToken)
        elif pos == -1:
            if self.options.hasShortOption(token):
                opt = self.options.getOption(token)
                if opt is not None:
                    self.handleOption(opt)
            elif len(self.getMatchingLongOptions(token)) > 0:
                self.handleLongOptionWithoutEqual(hyphenToken)
            else:
                opt_name = self.getLongPrefix(token)
                if opt_name is not None and self.options.getOption(opt_name) and self.options.getOption(opt_name).acceptsArg():  # type: ignore
                    self.handleOption(self.options.getOption(opt_name))  # type: ignore
                    if self.currentOption is not None:
                        self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[len(opt_name):]))
                        self.currentOption = None
                elif self.isJavaProperty(token):
                    self.handleOption(self.options.getOption(token[0]))  # type: ignore
                    if self.currentOption is not None:
                        self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[1:]))
                        self.currentOption = None
                else:
                    self.handleConcatenatedOptions(hyphenToken)
        else:
            opt = token[:pos]
            value = token[pos + 1:]
            if len(opt) == 1:
                option = self.options.getOption(opt)
                if option is not None and option.acceptsArg():
                    self.handleOption(option)
                    if self.currentOption is not None:
                        self.currentOption.processValue(value)
                        self.currentOption = None
                else:
                    self.handleUnknownToken(hyphenToken)
            elif self.isJavaProperty(opt):
                self.handleOption(self.options.getOption(opt[0]))  # type: ignore
                if self.currentOption is not None:
                    self.currentOption.processValue(opt[1:])
                    self.currentOption.processValue(value)
                    self.currentOption = None
            else:
                self.handleLongOptionWithEqual(hyphenToken)

    def handleToken(self, token: Optional[str]) -> None:
        if token is not None:
            self.currentToken = token
            if self.skipParsing:
                self._raw_args.append(token)
            elif token == "--":
                self.skipParsing = True
            elif self.currentOption is not None and self.currentOption.acceptsArg() and self.isArgument(token):
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOn(token))
            elif token.startswith("--"):
                self.handleLongOption(token)
            elif token.startswith("-") and token != "-":
                self.handleShortAndLongOption(token)
            else:
                self.handleUnknownToken(token)
            if self.currentOption is not None and not self.currentOption.acceptsArg():
                self.currentOption = None

    def handleUnknownToken(self, token: str) -> None:
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException("Unrecognized option: " + token, token)
        self._raw_args.append(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def isArgument(self, token: str) -> bool:
        return not self.isOption(token) or self.isNegativeNumber(token)

    def isJavaProperty(self, token: str) -> bool:
        opt = None if len(token) == 0 else token[0]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        t = token if pos == -1 else token[:pos]
        if len(self.getMatchingLongOptions(t)) > 0:
            return True
        if self.getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    def isOption(self, token: str) -> bool:
        return self.isLongOption(token) or self.isShortOption(token)

    def isShortOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find("=")
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token) or ""
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token) or ""
        return token

    def updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            key = option.getKey()
            if key in self.expectedOpts:
                self.expectedOpts.remove(key)

        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                if group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)
