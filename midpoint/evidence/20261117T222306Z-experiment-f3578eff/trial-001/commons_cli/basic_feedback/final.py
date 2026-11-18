import copy
from typing import List, Optional, Any

class ParseException(Exception):
    def __init__(self, message_or_cause=None):
        super().__init__(str(message_or_cause) if message_or_cause is not None else "")
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e: BaseException) -> 'ParseException':
        if isinstance(e, ParseException):
            return e
        return ParseException(e)


class UnrecognizedOptionException(ParseException):
    def __init__(self, message: str, option: Optional[str] = None):
        super().__init__(message)
        self.option = option

    def getOption(self) -> Optional[str]:
        return self.option


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
    def __init__(self, missing_options_or_msg):
        if isinstance(missing_options_or_msg, list):
            msg = "Missing required option" + ("" if len(missing_options_or_msg) == 1 else "s") + ": "
            msg += ", ".join(str(o) for o in missing_options_or_msg)
            super().__init__(msg)
            self.missingOptions = list(missing_options_or_msg)
        else:
            super().__init__(str(missing_options_or_msg))
            self.missingOptions = []

    def getMissingOptions(self) -> list:
        return self.missingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg, option: Optional['Option'] = None):
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


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matching_options: list):
        buf = [f"Ambiguous option: '{option}'  (could be: "]
        buf.append(", ".join(f"'{opt}'" for opt in matching_options))
        buf.append(")")
        super().__init__("".join(buf), option)
        self.matchingOptions = list(matching_options)

    def getMatchingOptions(self) -> list:
        return self.matchingOptions


def _is_java_identifier_part(c: str) -> bool:
    if not c:
        return False
    return c.isalnum() or c == '_' or c == '$'


class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def is_valid_char(c: str) -> bool:
        return _is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def is_valid_opt(c: str) -> bool:
        return _is_java_identifier_part(c) or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @classmethod
    def validate(cls, option: Optional[str]) -> Optional[str]:
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


class Util:
    @staticmethod
    def strip_leading_hyphens(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        if s.startswith("--"):
            return s[2:]
        if s.startswith("-"):
            return s[1:]
        return s

    @staticmethod
    def strip_leading_and_trailing_quotes(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        length = len(s)
        if length > 1 and s.startswith('"') and s.endswith('"') and s[1:-1].find('"') == -1:
            return s[1:-1]
        return s


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, opt: Optional[str], longOpt: Optional[str] = None, hasArg: bool = False, description: Optional[str] = None):
        if opt is None and longOpt is None:
            raise ValueError("Either opt or longOpt must be specified")
        self.option = OptionValidator.validate(opt)
        self.longOption = longOpt
        self.argCount = 1 if hasArg else self.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.type = str
        self.values: List[str] = []
        self.valueSeparator = '\0'
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

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def hasOptionalArg(self) -> bool:
        return self.optionalArg

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

    def getKey(self) -> str:
        return self.longOption if self.option is None else self.option

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int) -> None:
        self.argCount = num

    def getValue(self, index: int = 0) -> Optional[str]:
        if not self.values or index < 0 or index >= len(self.values):
            return None
        return self.values[index]

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if self.values else None

    def getValuesList(self) -> List[str]:
        return self.values

    def clearValues(self) -> None:
        self.values.clear()

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

    def _add(self, val: str) -> None:
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(val)

    def processValue(self, value: str) -> None:
        if self.argCount == self.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add = value
        if self.valueSeparator != '\0':
            sep = self.valueSeparator
            idx = add.find(sep)
            while idx != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add[:idx])
                add = add[idx + 1:]
                idx = add.find(sep)
        self._add(add)

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
        return f"Option({self.option!r}, {self.longOption!r})"


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

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

    def hasOption(self, opt: str) -> bool:
        clean = Util.strip_leading_hyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasLongOption(self, opt: str) -> bool:
        clean = Util.strip_leading_hyphens(opt)
        return clean in self.longOpts

    def hasShortOption(self, opt: str) -> bool:
        clean = Util.strip_leading_hyphens(opt)
        return clean in self.shortOpts

    def getOption(self, opt: str) -> Optional[Option]:
        clean = Util.strip_leading_hyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getMatchingOptions(self, opt: str) -> List[str]:
        clean = Util.strip_leading_hyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matches = []
        for long_opt in self.longOpts:
            if long_opt.startswith(clean):
                matches.append(long_opt)
        return matches

    def getRequiredOptions(self) -> List[str]:
        return list(self.requiredOpts)

    def getOptionGroup(self, opt: Option) -> Any:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> List[Any]:
        return list(set(self.optionGroups.values()))

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())


class CommandLine:
    def __init__(self, args: Optional[List[str]] = None, options: Optional[List[Option]] = None):
        self.args: List[str] = list(args) if args else []
        self.options: List[Option] = list(options) if options else []

    def addArg(self, arg: Optional[str]) -> None:
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt: Optional[Option]) -> None:
        if opt is not None:
            self.options.append(opt)

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = Util.strip_leading_hyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt: Any) -> bool:
        if isinstance(opt, Option):
            return opt in self.options
        resolved = self._resolveOption(opt)
        return resolved is not None

    def getOptionValues(self, opt: Any) -> Optional[List[str]]:
        if not isinstance(opt, Option):
            opt = self._resolveOption(opt)
        if opt is None:
            return None
        values = []
        for processedOption in self.options:
            if processedOption == opt:
                values.extend(processedOption.getValuesList())
        return values if len(values) > 0 else None

    def getOptionValue(self, opt: Any, defaultValue: Optional[str] = None) -> Optional[str]:
        vals = self.getOptionValues(opt)
        return vals[0] if vals is not None and len(vals) > 0 else defaultValue

    def getArgs(self) -> List[str]:
        return list(self.args)

    def getArgList(self) -> List[str]:
        return self.args

    def getOptions(self) -> List[Option]:
        return list(self.options)


class DefaultParser:
    def __init__(self, allowPartialMatching: bool = True):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes: Optional[bool] = None
        self.cmd: CommandLine = CommandLine()
        self.options: Options = Options()
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
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = Util.strip_leading_hyphens(token)
        if t is None:
            return None
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

    def _handleOption(self, option: Option) -> None:
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _updateRequiredOptions(self, option: Option) -> None:
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                if group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)

    def _handleConcatenatedOptions(self, token: str) -> None:
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self._handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            self._handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self._stripQuotesDefaultOff(token[i + 1:]))
                break

    def _handleLongOption(self, token: str) -> None:
        pos = token.find('=')
        if pos == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleLongOptionWithEqual(self, token: str) -> None:
        pos = token.find('=')
        value = token[pos + 1:]
        opt = token[:pos]
        matching_opts = self._getMatchingLongOptions(opt)
        if not matching_opts:
            self._handleUnknownToken(self.currentToken)
        elif len(matching_opts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matching_opts)
        else:
            key = opt if self.options.hasLongOption(opt) else matching_opts[0]
            option = self.options.getOption(key)
            if option is not None and option.acceptsArg():
                self._handleOption(option)
                if self.currentOption is not None:
                    self.currentOption.processValue(self._stripQuotesDefaultOff(value))
                self.currentOption = None
            else:
                self._handleUnknownToken(self.currentToken)

    def _handleLongOptionWithoutEqual(self, token: str) -> None:
        matching_opts = self._getMatchingLongOptions(token)
        if not matching_opts:
            self._handleUnknownToken(self.currentToken)
        elif len(matching_opts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matching_opts)
        else:
            key = token if self.options.hasLongOption(token) else matching_opts[0]
            self._handleOption(self.options.getOption(key))

    def _handleShortAndLongOption(self, hyphenToken: str) -> None:
        token = Util.strip_leading_hyphens(hyphenToken)
        if token is None:
            return
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
                    if self.currentOption is not None:
                        self.currentOption.processValue(self._stripQuotesDefaultOff(token[len(opt):]))
                    self.currentOption = None
                elif self._isJavaProperty(token):
                    self._handleOption(self.options.getOption(token[:1]))
                    if self.currentOption is not None:
                        self.currentOption.processValue(self._stripQuotesDefaultOff(token[1:]))
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
                    if self.currentOption is not None:
                        self.currentOption.processValue(value)
                    self.currentOption = None
                else:
                    self._handleUnknownToken(hyphenToken)
            elif self._isJavaProperty(opt):
                self._handleOption(self.options.getOption(opt[:1]))
                if self.currentOption is not None:
                    self.currentOption.processValue(opt[1:])
                    self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self._handleLongOptionWithEqual(hyphenToken)

    def _handleToken(self, token: Optional[str]) -> None:
        if token is None:
            return
        self.currentToken = token
        if self.skipParsing:
            self.cmd.addArg(token)
        elif token == "--":
            self.skipParsing = True
        elif self.currentOption is not None and self.currentOption.acceptsArg() and self._isArgument(token):
            self.currentOption.processValue(self._stripQuotesDefaultOn(token))
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

    def _isJavaProperty(self, token: str) -> bool:
        if not token:
            return False
        opt = token[:1]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def _isLongOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        t = token if pos == -1 else token[:pos]
        if len(self._getMatchingLongOptions(t)) > 0:
            return True
        if self._getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return token.startswith("-")
        except ValueError:
            return False

    def _isOption(self, token: str) -> bool:
        return self._isLongOption(token) or self._isShortOption(token)

    def _isShortOption(self, token: Optional[str]) -> bool:
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def _stripQuotesDefaultOff(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes:
            return Util.strip_leading_and_trailing_quotes(token) or ""
        return token

    def _stripQuotesDefaultOn(self, token: str) -> str:
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.strip_leading_and_trailing_quotes(token) or ""
        return token
