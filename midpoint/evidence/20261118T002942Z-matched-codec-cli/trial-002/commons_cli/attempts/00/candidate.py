import copy

class ParseException(Exception):
    def __init__(self, message_or_cause):
        super().__init__(str(message_or_cause))
        self.cause = message_or_cause if isinstance(message_or_cause, Exception) else None

    @staticmethod
    def wrap(e):
        if isinstance(e, UnsupportedOperationException):
            raise e
        if isinstance(e, ParseException):
            return e
        return ParseException(e)

class UnsupportedOperationException(Exception):
    pass

class AlreadySelectedException(ParseException):
    def __init__(self, message_or_group=None, option=None):
        if isinstance(message_or_group, str):
            super().__init__(message_or_group)
            self.group = None
            self.option = None
        else:
            group = message_or_group
            msg = f"The option '{option.getKey() if option else None}' was specified but an option from this group has already been selected: '{group.getSelected() if group else None}'"
            super().__init__(msg)
            self.group = group
            self.option = option

    def getOption(self):
        return self.option

    def getOptionGroup(self):
        return self.group

class UnrecognizedOptionException(ParseException):
    def __init__(self, message, option=None):
        super().__init__(message)
        self.option = option

    def getOption(self):
        return self.option

class AmbiguousOptionException(UnrecognizedOptionException):
    def __init__(self, option, matchingOptions):
        msg = f"Ambiguous option: '{option}'  (could be: " + ", ".join(f"'{o}'" for o in matchingOptions) + ")"
        super().__init__(msg, option)
        self.matchingOptions = list(matchingOptions)

    def getMatchingOptions(self):
        return self.matchingOptions

class MissingArgumentException(ParseException):
    def __init__(self, option_or_message):
        if isinstance(option_or_message, Option):
            super().__init__(f"Missing argument for option: {option_or_message.getKey()}")
            self.option = option_or_message
        else:
            super().__init__(option_or_message)
            self.option = None

    def getOption(self):
        return self.option

class MissingOptionException(ParseException):
    def __init__(self, missingOptions_or_message):
        if isinstance(missingOptions_or_message, list):
            missingOptions = missingOptions_or_message
            msg = "Missing required option" + ("" if len(missingOptions) == 1 else "s") + ": " + ", ".join(str(o) for o in missingOptions)
            super().__init__(msg)
            self.missingOptions = missingOptions
        else:
            super().__init__(missingOptions_or_message)
            self.missingOptions = None

    def getMissingOptions(self):
        return self.missingOptions

class OptionValidator:
    ADDITIONAL_OPTION_CHARS = {'?', '@'}
    ADDITIONAL_LONG_CHARS = {'-'}

    @staticmethod
    def isValidChar(c):
        return c.isalnum() or c == '_' or c in OptionValidator.ADDITIONAL_LONG_CHARS

    @staticmethod
    def isValidOpt(c):
        return c.isalnum() or c == '_' or c in OptionValidator.ADDITIONAL_OPTION_CHARS

    @staticmethod
    def validate(option):
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
    EMPTY_STRING_ARRAY = []

    @staticmethod
    def isEmpty(val):
        return val is None or len(val) == 0

    @staticmethod
    def stripLeadingAndTrailingQuotes(str_val):
        if Util.isEmpty(str_val):
            return str_val
        length = len(str_val)
        if length > 1 and str_val.startswith('"') and str_val.endswith('"') and str_val[1:length-1].find('"') == -1:
            return str_val[1:length-1]
        return str_val

    @staticmethod
    def stripLeadingHyphens(str_val):
        if Util.isEmpty(str_val):
            return str_val
        if str_val.startswith("--"):
            return str_val[2:]
        if str_val.startswith("-"):
            return str_val[1:]
        return str_val

class Option:
    UNINITIALIZED = -1
    UNLIMITED_VALUES = -2

    def __init__(self, option, longOption=None, hasArg=False, description=None):
        if longOption is None and not isinstance(hasArg, bool):
            description = hasArg
            hasArg = bool(longOption)
            longOption = None
        elif isinstance(longOption, bool):
            description = hasArg
            hasArg = longOption
            longOption = None

        self.option = OptionValidator.validate(option)
        self.longOption = longOption
        self.argCount = 1 if hasArg else Option.UNINITIALIZED
        self.description = description
        self.required = False
        self.optionalArg = False
        self.argName = None
        self.values = []
        self.valueSeparator = '\0'
        self.deprecated = None
        self.since = None
        self.converter = None
        self.type = str

    def acceptsArg(self):
        return (self.hasArg() or self.hasArgs() or self.hasOptionalArg()) and (self.argCount <= 0 or len(self.values) < self.argCount)

    def requiresArg(self):
        if self.optionalArg:
            return False
        if self.argCount == Option.UNLIMITED_VALUES:
            return len(self.values) == 0
        return self.acceptsArg()

    def add(self, value):
        if not self.acceptsArg():
            raise ValueError("Cannot add value, list full.")
        self.values.append(value)

    def processValue(self, value):
        if self.argCount == Option.UNINITIALIZED:
            raise ValueError("NO_ARGS_ALLOWED")
        add_val = value
        if self.hasValueSeparator():
            sep = self.valueSeparator
            index = add_val.find(sep)
            while index != -1:
                if len(self.values) == self.argCount - 1:
                    break
                self.add(add_val[:index])
                add_val = add_val[index + 1:]
                index = add_val.find(sep)
        self.add(add_val)

    def clearValues(self):
        self.values.clear()

    def clone(self):
        opt = copy.copy(self)
        opt.values = list(self.values)
        return opt

    def getOpt(self):
        return self.option

    def getLongOpt(self):
        return self.longOption

    def setLongOpt(self, longOpt):
        self.longOption = longOpt

    def getKey(self):
        return self.longOption if self.option is None else self.option

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    def hasArg(self):
        return self.argCount > 0 or self.argCount == Option.UNLIMITED_VALUES

    def hasArgs(self):
        return self.argCount > 1 or self.argCount == Option.UNLIMITED_VALUES

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = required

    def getValue(self, index=0):
        if isinstance(index, str):
            val = self.getValue(0)
            return val if val is not None else index
        if len(self.values) == 0:
            return None
        return self.values[index]

    def getValues(self):
        return list(self.values) if len(self.values) > 0 else None

    def getValuesList(self):
        return self.values

    def hasOptionalArg(self):
        return self.optionalArg

    def setOptionalArg(self, optionalArg):
        self.optionalArg = optionalArg

    def hasValueSeparator(self):
        return self.valueSeparator != '\0' and ord(self.valueSeparator) > 0

    def getValueSeparator(self):
        return self.valueSeparator

    def setValueSeparator(self, sep):
        self.valueSeparator = sep

    def isDeprecated(self):
        return self.deprecated is not None

    def getArgs(self):
        return self.argCount

    def setArgs(self, num):
        self.argCount = num

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Option):
            return False
        return self.longOption == other.longOption and self.option == other.option

    def __hash__(self):
        return hash((self.longOption, self.option))

class OptionGroup:
    def __init__(self):
        self.optionMap = {}
        self.selected = None
        self.required = False

    def addOption(self, option):
        self.optionMap[option.getKey()] = option
        return self

    def getNames(self):
        return list(self.optionMap.keys())

    def getOptions(self):
        return list(self.optionMap.values())

    def getSelected(self):
        return self.selected

    def isRequired(self):
        return self.required

    def setRequired(self, required):
        self.required = required

    def isSelected(self):
        return self.selected is not None

    def setSelected(self, option):
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

    def addOption(self, opt, longOpt=None, hasArg=False, description=None):
        if not isinstance(opt, Option):
            opt = Option(opt, longOpt, hasArg, description)
        key = opt.getKey()
        if opt.hasLongOpt():
            self.longOpts[opt.getLongOpt()] = opt
        if opt.isRequired():
            if key in self.requiredOpts:
                self.requiredOpts.remove(key)
            self.requiredOpts.append(key)
        self.shortOpts[key] = opt
        return self

    def addOptionGroup(self, group):
        if group.isRequired():
            self.requiredOpts.append(group)
        for option in group.getOptions():
            option.setRequired(False)
            self.addOption(option)
            self.optionGroups[option.getKey()] = group
        return self

    def addOptions(self, options):
        for opt in options.getOptions():
            if self.hasOption(opt.getKey()):
                raise ValueError(f"Duplicate key: {opt.getKey()}")
            self.addOption(opt)
        for group in options.getOptionGroups():
            self.addOptionGroup(group)
        return self

    def addRequiredOption(self, opt, longOpt, hasArg, description):
        option = Option(opt, longOpt, hasArg, description)
        option.setRequired(True)
        self.addOption(option)
        return self

    def getMatchingOptions(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        if clean in self.longOpts:
            return [clean]
        return [longOpt for longOpt in self.longOpts if longOpt.startswith(clean)]

    def getOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return self.shortOpts.get(clean, self.longOpts.get(clean))

    def getOptionGroup(self, opt):
        key = opt.getKey() if isinstance(opt, Option) else opt
        return self.optionGroups.get(key)

    def getOptionGroups(self):
        return list(set(self.optionGroups.values()))

    def getOptions(self):
        return list(self.shortOpts.values())

    def getRequiredOptions(self):
        return list(self.requiredOpts)

    def hasLongOption(self, opt):
        return Util.stripLeadingHyphens(opt) in self.longOpts

    def hasOption(self, opt):
        clean = Util.stripLeadingHyphens(opt)
        return clean in self.shortOpts or clean in self.longOpts

    def hasShortOption(self, opt):
        return Util.stripLeadingHyphens(opt) in self.shortOpts

class CommandLine:
    def __init__(self, args=None, options=None):
        self.args = list(args) if args is not None else []
        self.options = list(options) if options is not None else []

    def addArg(self, arg):
        if arg is not None:
            self.args.append(arg)

    def addOption(self, opt):
        if opt is not None:
            self.options.append(opt)

    def getArgList(self):
        return self.args

    def getArgs(self):
        return list(self.args)

    def getOptions(self):
        return list(self.options)

    def _resolveOption(self, opt):
        if isinstance(opt, Option):
            return opt
        actual = Util.stripLeadingHyphens(opt)
        if actual is not None:
            for option in self.options:
                if actual == option.getOpt() or actual == option.getLongOpt():
                    return option
        return None

    def hasOption(self, opt):
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return False
            return self.hasOption(opt.getSelected())
        option = self._resolveOption(opt)
        return option in self.options if option else False

    def getOptionValues(self, opt):
        if isinstance(opt, OptionGroup):
            if opt is None or not opt.isSelected():
                return None
            return self.getOptionValues(opt.getSelected())
        option = self._resolveOption(opt)
        if option is None:
            return None
        res = []
        for processedOption in self.options:
            if processedOption == option:
                res.extend(processedOption.getValuesList())
        return res if len(res) > 0 else None

    def getOptionValue(self, opt, defaultValue=None):
        if callable(defaultValue):
            defaultValue = defaultValue()
        values = self.getOptionValues(opt)
        if values is None:
            return defaultValue
        return values[0]

class DefaultParser:
    def __init__(self, allowPartialMatching=True, stripLeadingAndTrailingQuotes=None):
        self.allowPartialMatching = allowPartialMatching
        self.stripLeadingAndTrailingQuotes = stripLeadingAndTrailingQuotes
        self.cmd = None
        self.options = None
        self.stopAtNonOption = False
        self.currentToken = None
        self.currentOption = None
        self.skipParsing = False
        self.expectedOpts = []

    def parse(self, options, arguments, properties_or_stopAtNonOption=False, stopAtNonOption=False):
        if isinstance(properties_or_stopAtNonOption, bool):
            stopAtNonOption = properties_or_stopAtNonOption
            properties = None
        else:
            properties = properties_or_stopAtNonOption

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
        self.handleProperties(properties)
        self.checkRequiredOptions()
        return self.cmd

    def checkRequiredArgs(self):
        if self.currentOption is not None and self.currentOption.requiresArg():
            if self.isJavaProperty(self.currentOption.getKey()) and len(self.currentOption.getValuesList()) == 1:
                return
            raise MissingArgumentException(self.currentOption)

    def checkRequiredOptions(self):
        if len(self.expectedOpts) > 0:
            raise MissingOptionException(self.expectedOpts)

    def getLongPrefix(self, token):
        t = Util.stripLeadingHyphens(token)
        opt = None
        for i in range(len(t) - 2, 1, -1):
            prefix = t[:i]
            if self.options.hasLongOption(prefix):
                opt = prefix
                break
        return opt

    def getMatchingLongOptions(self, token):
        if self.allowPartialMatching:
            return self.options.getMatchingOptions(token)
        matches = []
        if self.options.hasLongOption(token):
            matches.append(self.options.getOption(token).getLongOpt())
        return matches

    def handleConcatenatedOptions(self, token):
        for i in range(1, len(token)):
            ch = token[i]
            if not self.options.hasOption(ch):
                self.handleUnknownToken(token[i:] if self.stopAtNonOption and i > 1 else token)
                break
            self.handleOption(self.options.getOption(ch))
            if self.currentOption is not None and len(token) != i + 1:
                self.currentOption.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(token[i + 1:]))
                break

    def handleLongOption(self, token):
        if token.find('=') == -1:
            self.handleLongOptionWithoutEqual(token)
        else:
            self.handleLongOptionWithEqual(token)

    def handleLongOptionWithEqual(self, token):
        pos = token.find('=')
        value = token[pos + 1:]
        opt = token[:pos]
        matchingOpts = self.getMatchingLongOptions(opt)
        if len(matchingOpts) == 0:
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

    def handleLongOptionWithoutEqual(self, token):
        matchingOpts = self.getMatchingLongOptions(token)
        if len(matchingOpts) == 0:
            self.handleUnknownToken(self.currentToken)
        elif len(matchingOpts) > 1 and not self.options.hasLongOption(token):
            raise AmbiguousOptionException(token, matchingOpts)
        else:
            key = token if self.options.hasLongOption(token) else matchingOpts[0]
            self.handleOption(self.options.getOption(key))

    def handleOption(self, option):
        self.checkRequiredArgs()
        copy_opt = option.clone()
        self.updateRequiredOptions(copy_opt)
        self.cmd.addOption(copy_opt)
        self.currentOption = copy_opt if copy_opt.hasArg() else None

    def handleProperties(self, properties):
        if properties is None:
            return
        for option in properties.keys():
            opt = self.options.getOption(option)
            if opt is None:
                raise UnrecognizedOptionException("Default option wasn't defined", option)
            group = self.options.getOptionGroup(opt)
            selected = group is not None and group.isSelected()
            if not self.cmd.hasOption(option) and not selected:
                value = properties[option]
                if opt.hasArg():
                    if Util.isEmpty(opt.getValues()):
                        opt.processValue(self.stripLeadingAndTrailingQuotesDefaultOff(value))
                elif value.lower() not in ("yes", "true", "1"):
                    continue
                self.handleOption(opt)
                self.currentOption = None

    def handleShortAndLongOption(self, hyphenToken):
        token = Util.stripLeadingHyphens(hyphenToken)
        pos = token.find('=')
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

    def handleToken(self, token):
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

    def handleUnknownToken(self, token):
        if token.startswith("-") and len(token) > 1 and not self.stopAtNonOption:
            raise UnrecognizedOptionException(f"Unrecognized option: {token}", token)
        self.cmd.addArg(token)
        if self.stopAtNonOption:
            self.skipParsing = True

    def isArgument(self, token):
        return not self.isOption(token) or self.isNegativeNumber(token)

    def isJavaProperty(self, token):
        opt = None if len(token) == 0 else token[0]
        option = self.options.getOption(opt)
        return option is not None and (option.getArgs() >= 2 or option.getArgs() == Option.UNLIMITED_VALUES)

    def isLongOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        t = token if pos == -1 else token[:pos]
        if len(self.getMatchingLongOptions(t)) > 0:
            return True
        if self.getLongPrefix(token) is not None and not token.startswith("--"):
            return True
        return False

    def isNegativeNumber(self, token):
        try:
            float(token)
            return True
        except ValueError:
            return False

    def isOption(self, token):
        return self.isLongOption(token) or self.isShortOption(token)

    def isShortOption(self, token):
        if token is None or not token.startswith("-") or len(token) == 1:
            return False
        pos = token.find('=')
        optName = token[1:] if pos == -1 else token[1:pos]
        if self.options.hasShortOption(optName):
            return True
        return len(optName) > 0 and self.options.hasShortOption(optName[0])

    def stripLeadingAndTrailingQuotesDefaultOff(self, token):
        if self.stripLeadingAndTrailingQuotes is not None and self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def stripLeadingAndTrailingQuotesDefaultOn(self, token):
        if self.stripLeadingAndTrailingQuotes is None or self.stripLeadingAndTrailingQuotes:
            return Util.stripLeadingAndTrailingQuotes(token)
        return token

    def updateRequiredOptions(self, option):
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
