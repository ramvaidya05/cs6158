import copy
import math
from typing import Optional, List, Any


class ParseException(Exception):
    def __init__(self, message_or_cause=None):
        super().__init__(str(message_or_cause) if message_or_cause is not None else "")
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e: Exception) -> "ParseException":
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
    def __init__(self, message_or_opt):
        if isinstance(message_or_opt, Option):
            super().__init__(f"Missing argument for option: {message_or_opt.getKey()}")
            self.option = message_or_opt
        else:
            super().__init__(str(message_or_opt))
            self.option = None

    def getOption(self) -> Optional["Option"]:
        return self.option


class MissingOptionException(ParseException):
    def __init__(self, missing_options_or_msg):
        if isinstance(missing_options_or_msg, list):
            msg = MissingOptionException.create_message(missing_options_or_msg)
            super().__init__(msg)
            self.missingOptions = missing_options_or_msg
        else:
            super().__init__(str(missing_options_or_msg))
            self.missingOptions = []

    @staticmethod
    def create_message(missing_options: list) -> str:
        s = "Missing required option" + ("" if len(missing_options) == 1 else "s") + ": "
        return s + ", ".join(str(opt) for opt in missing_options)

    def getMissingOptions(self) -> list:
        return self.missingOptions


class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option: str, matching_options: list):
        super().__init__(AmbiguousOptionException.create_message(option, matching_options), option)
        self.matchingOptions = list(matching_options)

    @staticmethod
    def create_message(option: str, matching_options: list) -> str:
        opts_str = ", ".join(f"'{opt}'" for opt in matching_options)
        return f"Ambiguous option: '{option}'  (could be: {opts_str})"

    def getMatchingOptions(self) -> list:
        return self.matchingOptions


class AlreadySelectedException(ParseException):
    def __init__(self, group_or_msg, option: Optional["Option"] = None):
        if option is not None:
            group = group_or_msg
            msg = f"The option '{option.getKey()}' was specified but an option from this group has already been selected: '{group.getSelected()}'"
            super().__init__(msg)
            self.group = group
            self.option = option
        else:
            super().__init__(str(group_or_msg))
            self.group = None
            self.option = None

    def getOption(self) -> Optional["Option"]:
        return self.option

    def getOptionGroup(self) -> Any:
        return self.group


class _Util:
    @staticmethod
    def isEmpty(val) -> bool:
        return val is None or len(val) == 0

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
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def is_java_identifier_part(c: str) -> bool:
        if c.isalnum() or c in ('$', '_'):
            return True
        return False

    @staticmethod
    def isValidOpt(c: str) -> bool:
        return _OptionValidator.is_java_identifier_part(c) or c in _OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def isValidChar(c: str) -> bool:
        return _OptionValidator.is_java_identifier_part(c) or c in _OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def validate(option: Optional[str]) -> Optional[str]:
        if option is None:
            return None
        if len(option) == 0:
            raise ValueError("Empty option name.")
        ch0 = option[0]
        if not _OptionValidator.isValidOpt(ch0):
            raise ValueError(f"Illegal option name '{ch0}'.")
        if len(option) > 1:
            for ch in option[1:]:
                if not _OptionValidator.isValidChar(ch):
                    raise ValueError(f"The option '{option}' contains an illegal character : '{ch}'.")
        return option


class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option: Optional[str], long_option: Optional[str] = None, has_arg: bool = False, description: Optional[str] = None):
        if isinstance(long_option, bool) and description is None:
            description = has_arg
            has_arg = long_option
            long_option = None

        self.option = _OptionValidator.validate(option)
        self.longOption = long_option
        self.argCount = 1 if has_arg else Option.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.values: List[str] = []
        self.valueSeparator = '\0'
        self.argName = None
        self.since = None
        self.deprecated = None
        self.converter = None
        self.type = str

    def acceptsArg(self) -> bool:
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (
            self.argCount <= 0 or len(self.values) < self.argCount
        )

    def requiresArg(self) -> bool:
        if self.optionalArg:
            return False
        if self.argCount == Option.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def _add(self, value: str):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value: str):
        if self.argCount == Option.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add_str = value
        if self.hasValueSeparator():
            sep = self.valueSeparator
            index = add_str.find(sep)
            while index != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self._add(add_str[:index])
                add_str = add_str[index + 1:]
                index = add_str.find(sep)
        self._add(add_str)

    def clearValues(self):
        self.values.clear()

    def getOpt(self) -> Optional[str]:
        return self.option

    def getLongOpt(self) -> Optional[str]:
        return self.longOption

    def getKey(self) -> Optional[str]:
        return self.longOption if self.option is None else self.option

    def hasArg(self) -> bool:
        return self.argCount > 0 or self.argCount == Option.UNLIMITED_VALUES

    def hasArgs(self) -> bool:
        return self.argCount > 1 or self.argCount == Option.UNLIMITED_VALUES

    def hasLongOpt(self) -> bool:
        return self.longOption is not None

    def hasOptionalArg(self) -> bool:
        return self.optionalArg

    def hasValueSeparator(self) -> bool:
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def isRequired(self) -> bool:
        return self.required

    def setRequired(self, required: bool) -> None:
        self.required = required

    def getValue(self, default_value_or_index=None) -> Optional[str]:
        if isinstance(default_value_or_index, int):
            if len(self.values) == 0:
                return None
            return self.values[default_value_or_index]
        if len(self.values) == 0:
            return default_value_or_index
        return self.values[0]

    def getValues(self) -> Optional[List[str]]:
        return list(self.values) if len(self.values) > 0 else None

    def getValuesList(self) -> List[str]:
        return self.values

    def getArgs(self) -> int:
        return self.argCount

    def setArgs(self, num: int):
        self.argCount = num

    def isDeprecated(self) -> bool:
        return self.deprecated is not None

    def clone(self) -> "Option":
        copied = copy.copy(self)
        copied.values = list(self.values)
        return copied

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self) -> int:
        return hash((self.longOption, self.option))


class Options:
    def __init__(self):
        self.shortOpts = {}
        self.longOpts = {}
        self.requiredOpts = []
        self.optionGroups = {}

    def addOption(self, opt_or_str, *args) -> "Options":
        if isinstance(opt_or_str, Option):
            opt = opt_or_str
            key = opt.getKey()
            if opt.hasLongOpt():
                self.longOpts[opt.getLongOpt()] = opt
            if opt.isRequired():
                if key in self.requiredOpts:
                    self.requiredOpts.remove(key)
                self.requiredOpts.append(key)
            self.shortOpts[key] = opt
            return self
        else:
            opt_str = opt_or_str
            if len(args) == 1:
                return self.addOption(Option(opt_str, None, False, args[0]))
            elif len(args) == 2:
                return self.addOption(Option(opt_str, None, args[0], args[1]))
            elif len(args) == 3:
                return self.addOption(Option(opt_str, args[0], args[1], args[2]))
            else:
                raise ValueError("Invalid arguments for addOption")

    def hasOption(self, opt: Optional[str]) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasLongOption(self, opt: Optional[str]) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.longOpts

    def hasShortOption(self, opt: Optional[str]) -> bool:
        clean = _Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts

    def getOption(self, opt: Optional[str]) -> Optional[Option]:
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.shortOpts:
            return self.shortOpts[clean]
        return self.longOpts.get(clean)

    def getMatchingOptions(self, opt: Optional[str]) -> List[str]:
        clean = _Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        matches = []
        for long_opt in self.longOpts.keys():
            if long_opt.startswith(clean):
                matches.append(long_opt)
        return matches

    def getRequiredOptions(self) -> List[Any]:
        return list(self.requiredOpts)

    def getOptionGroup(self, opt: Option) -> Any:
        return self.optionGroups.get(opt.getKey())

    def getOptionGroups(self) -> List[Any]:
        return list(set(self.optionGroups.values()))

    def getOptions(self) -> List[Option]:
        return list(self.shortOpts.values())


class CommandLine:
    def __init__(self, args: Optional[List[str]] = None, options: Optional[List[Option]] = None):
        self.args: List[str] = args if args is not None else []
        self.options: List[Option] = options if options is not None else []

    def addArg(self, arg: Optional[str]):
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt: Optional[Option]):
        if opt is not None:
            self.options.append(opt)

    def getArgs(self) -> List[str]:
        return list(self.args)

    def getArgList(self) -> List[str]:
        return self.args

    def getOptions(self) -> List[Option]:
        return list(self.options)

    def hasOption(self, opt_or_option) -> bool:
        if isinstance(opt_or_option, Option):
            return opt_or_option in self.options
        return self._resolveOption(opt_or_option) is not None

    def getOptionValue(self, opt_or_option, default_value: Optional[str] = None) -> Optional[str]:
        values = self.getOptionValues(opt_or_option)
        if values is None or len(values) == 0:
            return default_value
        return values[0]

    def getOptionValues(self, opt_or_option) -> Optional[List[str]]:
        target_opt = opt_or_option if isinstance(opt_or_option, Option) else self._resolveOption(opt_or_option)
        if target_opt is None:
            return None
        values: List[str] = []
        for processed_option in self.options:
            if processed_option == target_opt:
                values.extend(processed_option.getValuesList())
        return values if len(values) > 0 else None

    def _resolveOption(self, opt: Optional[str]) -> Optional[Option]:
        actual = _Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None


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

    def _checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self._isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def _checkRequiredOptions(self):
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def _handleToken(self, token: Optional[str]):
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

    def _handleLongOption(self, token: str):
        pos = token.find("=")
        if pos == -1:
            self._handleLongOptionWithoutEqual(token)
        else:
            self._handleLongOptionWithEqual(token)

    def _handleLongOptionWithEqual(self, token: str):
        pos = token.find("=")
        value = token[pos + 1:]
        opt = token[:pos]
        matching_opts = self._getMatchingLongOptions(opt)
        if len(matching_opts) == 0:
            self._handleUnknownToken(self.currentToken)
        elif len(matching_opts) > 1 and not self.options.hasLongOption(opt):
            raise AmbiguousOptionException(opt, matching_opts)
        else:
            key = opt if self.options.hasLongOption(opt) else matching_opts[0]
            option = self.options.getOption(key)
            if option.acceptsArg():
                self._handleOption(option)
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(value))
                self.currentOption = None
            else:
                self._handleUnknownToken(self.currentToken)

    def _handleLongOptionWithoutEqual(self, token: str):
        matching_opts = self._getMatchingLongOptions(token)
        if len(matching_opts) == 0:
            self._handleUnknownToken(self.currentToken)
        elif len(matching_opts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matching_opts)
        else:
            key = token if self.options.hasLongOption(token) else matching_opts[0]
            self._handleOption(self.options.getOption(key))

    def _handleShortAndLongOption(self, hyphen_token: str):
        token = _Util.stripLeadingHyphens(hyphen_token)
        pos = token.find("=")
        if len(token) == 1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            else:
                self._handleUnknownToken(hyphen_token)
        elif pos == -1:
            if self.options.hasShortOption(token):
                self._handleOption(self.options.getOption(token))
            elif len(self._getMatchingLongOptions(token)) > 0:
                self._handleLongOptionWithoutEqual(hyphen_token)
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
                    self._handleConcatenatedOptions(hyphen_token)
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
                    self._handleUnknownToken(hyphen_token)
            elif self._isJavaProperty(opt):
                self._handleOption(self.options.getOption(opt[:1]))
                self.currentOption.processValue(opt[1:])
                self.currentOption.processValue(value)
                self.currentOption = None
            else:
                self._handleLongOptionWithEqual(hyphen_token)

    def _handleConcatenatedOptions(self, token: str):
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self._handleUnknownToken(token[i:] if (self.stopAtNonOption and i > 1) else token)
                break
            self._handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self._stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def _handleOption(self, option: Option):
        self._checkRequiredArgs()
        copy_opt = option.clone()
        self._updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def _updateRequiredOptions(self, option: Option):
        if option.isRequired():
            if option.getKey() in self.expectedOpts:
                self.expectedOpts.remove(option.getKey())
        group = self.options.getOptionGroup(option)
        if group is not None:
            if group.isRequired():
                if group in self.expectedOpts:
                    self.expectedOpts.remove(group)
            group.setSelected(option)

    def _handleUnknownToken(self, token: str):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def _getMatchingLongOptions(self, token: str) -> List[str]:
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def _getLongPrefix(self, token: str) -> Optional[str]:
        t = _Util.stripLeadingHyphens(token)
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def _isArgument(self, token: str) -> bool:
        return not self._isOption(token) or self._isNegativeNumber(token)

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
        opt_name = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(opt_name):
            return True
        return len(opt_name) > 0 and self.options.hasShortOption(opt_name[0])

    def _isNegativeNumber(self, token: str) -> bool:
        try:
            float(token)
            return token.startswith("-")
        except ValueError:
            return False

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
