import copy
from typing import List, Optional

class ParseException(Exception):
    def __init__(self, message_or_cause=""):
        super().__init__(str(message_or_cause))
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e):
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
    def __init__(self, option: str, matching_options: List[str]):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{o}'" for o in matching_options) + ")"
        super().__init__(msg, option)
        self.matching_options = list(matching_options)

    def getMatchingOptions(self) -> List[str]:
        return list(self.matching_options)


class MissingArgumentException(ParseException):
    def __init__(self, option_or_message):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option = option_or_message
        else:
            super().__init__(str(option_or_message))
            self.option = None

    def getOption(self):
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_options_or_message):
        if isinstance(missing_options_or_message, list):
            missing = missing_options_or_message
            msg = "Missing required option" + ("" if len(missing) == 1 else "s") + ": " + ", ".join(str(o) for o in missing)
            super().__init__(msg)
            self.missing_options = list(missing)
        else:
            super().__init__(str(missing_options_or_message))
            self.missing_options = None

    def getMissingOptions(self):
        return self.missing_options


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_message, option=None):
        if option is not None:
            group = group_or_message
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(msg)
            self.group = group
            self.option = option
        else:
            super().__init__(str(group_or_message))
            self.group = None
            self.option = None

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def _is_java_identifier_part(c: str) -> bool:
        return c.isalnum() or c == '$' or c == '_'

    @classmethod
    def _is_valid_opt(cls, c: str) -> bool:
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_OPTION_CHARS

    @classmethod
    def _is_valid_char(cls, c: str) -> bool:
        return cls._is_java_identifier_part(c) or c in cls.ADDITIONAL_LONG_CHARS

    @classmethod
    def validate(cls, option: Optional[str]) -> Optional[str]:
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

    def __init__(self, option: Optional[str], longOption: Optional[str], hasArg: bool, description: Optional[str]):
        self.option = OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.values: List[str] = []
        self.valueSeparator = '\0'
        self.argName: Optional[str] = None
        self.deprecated = None
        self.converter = None
        self.since: Optional[str] = None
        self.type = str

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

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = bool(required)

    def getKey(self) -> Optional[str]:
        return self.option if self.option is not None else self.longOption

    def getValue(self, default_value: Optional[str] = None) -> Optional[str]:
        if not self.values:
            return default_value
        return self.values[0]

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if self.values else None

    def getValuesList(self) -> List[str]:
        return self.values

    def getArgs(self) -> int:
        return self.argCount

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

    def toDeprecatedString(self) -> str:
        if not self.isDeprecated():
            return ""
        buf = f"Option '{self.option}'"
        if self.longOption is not None:
            buf += f"'{self.longOption}'"
        buf += f": {self.deprecated}"
        return buf

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

    def add(self, value: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def getValueSeparator(self) -> str:
        return self.valueSeparator

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
                self.add(add_val[:index])
                add_val = add_val[index + 1:]
                index = add_val.find(sep)
        self.add(add_val)

    def clearValues(self) -> None:
        self.values.clear()

    def clone(self) -> "Option":
        opt = copy.copy(self)
        opt.values = list(self.values)
        return opt

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
        self.selected: Optional[str] = None
        self.required: bool = False

    def addOption(self, option: Option) -> "OptionGroup":
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

    def addOption(self, opt: Option) -> "Options":
        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def addOptionGroup(self, group: OptionGroup) -> "Options":
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
        return Util.stripLeadingHyphens(opt) in self.longOpts

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
        matching = []
        for long_opt in self.longOpts:
            if long_opt.startswith(clean):
                matching.append(long_opt)
        return matching

    def getOptionGroup(self, opt: Option) -> Optional[OptionGroup]:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self):
        return list(set(self.optionGroups.values()))

    def getRequiredOptions(self) -> List[str]:
        return [str(o.getSelected()) if isinstance(o, OptionGroup) else str(o) for o in self.requiredOpts]


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

    def _resolve_option(self, opt: Optional[str]) -> Optional[Option]:
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt) -> bool:
        if isinstance(opt, Option):
            return opt in self.options
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        return self._resolve_option(opt) is not None

    def getOptionValue(self, opt, defaultValue=None) -> Optional[str]:
        values = self.getOptionValues(opt)
        if values is not None and len(values) > 0:
            return values[0]
        return defaultValue

    def getOptionValues(self, opt) -> Optional[List[str]]:
        target = None
        if isinstance(opt, OptionGroup):
            if not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        elif isinstance(opt, Option):
            target = opt
        else:
            target = self._resolve_option(opt)

        if target is None:
            return None

        values = []
        for processed in self.options:
            if processed == target:
                values.extend(processed.getValuesList())
        return values if values else None


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = None
        self.cmd: CommandLine = CommandLine()
        self.options: Optional[Options] = None
        self.stopAtNonOption: bool = False
        self.currentToken: Optional[str] = None
        self.currentOption: Optional[Option] = None
        self.skipParsing: bool = False
        self.expectedOpts: list = []

    def parse(self, options: Options, arguments: Optional[List[str]], stopAtNonOption: bool = False) -> CommandLine:
        self.options = options
        self.stopAtNonOption = stopAtNonOption
        self.skipParsing = False
        self.currentOption = None
        self.expectedOpts = list(options.requiredOpts)
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
        if self.expectedOpts:
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
            if opt.getLongOpt():
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
        if "=" not in token:
            self.handleLongOptionWithoutEqual(token)
        else:
            self.handleLongOptionWithEqual(token)

    def handleLongOptionWithEqual(self, token: str) -> None:
        pos = token.find("=")
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
        pos = token.find("=")
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
                    self.handleOption(self.options.getOption(token[:1]))
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
                self.handleOption(self.options.getOption(opt[:1]))
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
        opt = token[:1]
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
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired() and option.getKey() in self.expectedOpts:
            self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired() and group in self.expectedOpts:
                self.expectedOpts.remove(group)
            group.setSelected(option)

# Synthetic qualification additions (not model output).
def _get_description(self): return self.description
def _set_description(self, value): self.description = value
def _get_arg_name(self): return self.argName
def _set_arg_name(self, value): self.argName = value
def _set_optional(self, value): self.optionalArg = value
def _set_args(self, value): self.argCount = value
def _required(self): return list(self.requiredOpts)
Option.getDescription = _get_description
Option.setDescription = _set_description
Option.getArgName = _get_arg_name
Option.setArgName = _set_arg_name
Option.setOptionalArg = _set_optional
Option.setArgs = _set_args
Options.getRequiredOptions = _required

OptionGroup.setSelected = lambda self, option: setattr(self, "selected", option.getKey() if option else None)
