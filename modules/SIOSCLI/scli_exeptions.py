class SCLIExeptions(Exception):
    def __init__(self, message, arguments):
        """Base class for other SCLI exceptions"""
        Exception.__init__(self, message + ": {0}".format(arguments))
        self.ErrorMessage = message
        self.ErrorArguments = arguments
        pass


class BadArgumentsException(SCLIExeptions):
    """Raised when any bad args were submitted to a func"""

    pass


class SCLINativeExeption(SCLIExeptions):
    """Raised after an attempt to execute an SCLI command"""
    pass
