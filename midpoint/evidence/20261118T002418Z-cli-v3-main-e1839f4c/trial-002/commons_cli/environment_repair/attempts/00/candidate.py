from __future__ import annotations
import copy
from typing import Any, List, Optional, Set, Dict, Union


class ParseException(Exception):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message)
        self.message = message


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: Optional[str] = None, option: Optional[str] = None):
        super().__init__(message if message is not None else (f"Unrecognized option: {option}" if option else None))
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matchingOptions: List[str]):
        joined = ", ".join(f"'{opt}'" for opt in matchingOptions)
        msg = f"Ambiguous option: '{option}'  (could be: {joined})"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self) -> List[str]:
        return self.matchingOptions


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message: Union[Option, str]):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option: Optional[Option] = option_or_message
        else:
            super().__init__(option_or_message)
            self.option = None

    def getOption(self) -> Optional[Option]:
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_options_or_message: Union[List[Any], str]):
        if isinstance(missing_options_or_message, list):
            items = missing_options_or_message
            s = "Missing required option" + ("" if len(items) == 1 else "s") + ": " + ", ".join(str(x) for x in items)
            super().__init__(s)
            self.missingOptions: Optional[List[Any]] = items
        else:
            super().__init__(missing_options_or_message)
            self.missingOptions = None

    def getMissingOptions(self) -> Optional[List[Any]]:
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message: Union[OptionGroup, str], option: Optional[Option] = None):
        if isinstance(group_or_message, OptionGroup):
            group = group_or_message
            super().__init__(f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'")
            self.group: Optional[OptionGroup] = group
            self.option: Optional[Option] = option
        else:
            super().__init__(group_or_message)
            self.group = None
            self.option = None

    def getOption(self) -> Optional[Option]:
        return self.option

    def getOptionGroup(self) -> Optional[OptionGroup]:
        return self.group


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def _is_java_identifier_part(c: str) -> bool:
        return c.isalnum() or c in {'$', '_'}

    @staticmethod
    def isValidOpt(c: str) -> bool:
        return OptionValidator._is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def isValidChar(c: str) -> bool:
        return OptionValidator._is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_LONG_CHARS

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
        if length > 1 and s.startswith('"') and s.endswith('"') and ('"' not in s[1:length - 1]):
            return s[1:length - 1]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, opt: Optional[str], longOpt: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None):
        if opt is not None:
            self.option = OptionValidator.validate(opt)
        else:
            self.option = None
        self.longOption: Optional[str] = longOpt
        self.argCount: int = 1 if hasArg else self.UNINITIALIZED
        self.description: Optional[str] = description
        self.required: bool = False
        self.optionalArg: bool = False
        self.argName: Optional[str] = None
        self.values: List[str] = []
        self.valueSeparator: str = '\0'

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def setLongOpt(self, longOpt: Optional[str]) -> None:
        self.longOption = longOpt

    def hasArg(self) -> bool:
        return self.argCount > 0 or self.argCount == self.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self.argCount > 1 or self.argCount == self.UNLIMITED_VALUES

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def getValue(self) -> Optional[str]:
        return self.values[0] if self.values else None

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

    def getKey(self) -> Optional[str]:
        return self.option if self.option is not None else self.longOption

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator != '\0' and len(self.valueSeparator) > 0

    def getValueSeparator(self) -> str:
        return self.valueSeparator

    def setValueSeparator(self, sep: str) -> None:
        self.valueSeparator = sep

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (
            self.argCount <= 0 or len(self.values) < self.argCount
        )

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
        add = value
        if self.hasValueSeparator():
            sep = self.getValueSeparator()
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

    def clone(self) -> Option:
        opt = copy.copy(self)
        opt.values = list(self.values)
        return opt

    def isDeprecated(self) -> bool:
        return False

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self) -> int:
        return hash((self.longOption, self.option))

    def __repr__(self) -> str:
        return f"Option({self.getKey()})"


class OptionGroup:
    def __init__(self):
        self.optionMap: Dict[str, Option] = {}
        self.selected: Optional[str] = None
        self.required: bool = False

    def addOption(self, option: Option) -> OptionGroup:
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
        return f"OptionGroup({self.selected})"


class Options:
    def __init__(self):
        self.shortOpts: Dict[str, Option] = {}
        self.longOpts: Dict[str, Option] = {}
        self.requiredOpts: List[Any] = []
        self.optionGroups: Dict[str, OptionGroup] = {}

    def addOption(self, opt: Option) -> Options:
        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def addOptionGroup(self, group: OptionGroup) -> Options:
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
        return self.shortOpts.get(clean, self.longOpts.get(clean))

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> Set[OptionGroup]:
        return set(self.optionGroups.values())

    def getRequiredOptions(self) -> List[Any]:
        return list(self.requiredOpts)

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        return [longOpt for longOpt in self.longOpts.keys() if longOpt.startswith(clean)]

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())


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

    def _resolveOption(self, opt: str) -> Optional[Option]:
        clean = Util.stripLeadingHyphens(opt)
        if clean is not None:
            for option in self.options:
                if clean == option.getOpt() or clean == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Union[str, Option, OptionGroup]) -> bool:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        if isinstance(opt, Option):
            return opt in self.options
        return self._resolveOption(opt) is not None

    def getOptionValues(self, opt: Union[str, Option, OptionGroup]) -> Optional[List[str]]:
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        if isinstance(opt, str):
            resolved = self._resolveOption(opt)
            if resolved is None:
                return None
            target = resolved
        else:
            target = opt

        if target is None:
            return None

        values: List[str] = []
        for processedOption in self.options:
            if processedOption == target:
                values.extend(processedOption.getValuesList())
        return values if values else None

    def getOptionValue(self, opt: Union[str, Option, OptionGroup]) -> Optional[str]:
        values = self.getOptionValues(opt)
        return values[0] if values else None


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
                self.handleToken(argument)
        self.checkRequiredArgs()
        self.checkRequiredOptions()
        return self.cmd

    def checkRequiredArgs(self) -> None:
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self.isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def checkRequiredOptions(self) -> None:
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.stripLeadingHyphens(token)
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
            self.handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def handleLongOption(self, token: str) -> None:
        if self.indexOfEqual(token) == -1:
            self.handleLongOptionWithoutEqual(token)
        else:
            self.handleLongOptionWithEqual(token)

    def handleLongOptionWithEqual(self, token: str) -> None:
        pos = self.indexOfEqual(token)
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self.getMatchingLongOptions(opt)
        if not matchingOpts:
            self.handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matchingOpts)
        else:
            key = opt if self.options.hasLongOption(opt) else matchingOpts[0]
            option = self.options.getOption(key)
            if option.acceptsArg():
                self.handleOption(option)
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(value))
                self.currentOption = None
            else:
                self.handleUnknownToken(self.currentToken)

    def handleLongOptionWithoutEqual(self, token: str) -> None:
        matchingOpts = self.getMatchingLongOptions(token)
        if not matchingOpts:
            self.handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self.handleOption(self.options.getOption(key))

    def handleOption(self, option: Option) -> None:
        self.checkRequiredArgs()
        copy_opt = option.clone()
        self.updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = self.indexOfEqual(token)
        if len(token) == 1:
            if self.options.hasShortOption(token):
                self.handleOption(self.options.getOption(token))
            else:
                self.handleUnknownToken(hyphenToken)
        elif pos == -1:
            if self.options.hasShortOption(token):
                self.handleOption(self.options.getOption(token))
            elif len(self.getMatchingLongOptions(token)) > 0:
                self.handleLongOptionWithoutEqual(hyphenToken)
            else:
                opt = self.getLongPrefix(token)
                if opt is not None and self.options.getOption(opt).acceptsArg():
                    self.handleOption(self.options.getOption(opt))
                    self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[len(opt):]))
                    self.currentOption = None
                elif self.isJavaProperty(token):
                    self.handleOption(self.options.getOption(token[0]))
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
                    self.currentOption.processValue(value)
                    self.currentOption = None
                else:
                    self.handleUnknownToken(hyphenToken)
            elif self.isJavaProperty(opt):
                self.handleOption(self.options.getOption(opt[0]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self.handleLongOptionWithEqual(hyphenToken)

    def handleToken(self, token: Optional[str]) -> None:
        if token is not None:
            self.currentToken = token
            if self.skipParsing:
                self.cmd.addArg(token)
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
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def isArgument(self, token: str) -> bool:
        return not self.isOption(token) or self.isNegativeNumber(token)

    def isJavaProperty(self, token: Optional[str]) -> bool:
        if not token:
            return False
        opt = token[0]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = self.indexOfEqual(token)
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
        pos = self.indexOfEqual(token)
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def stripLeadingAndTrailingQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
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
