class NodeGlobalException(Exception):
    def __init__(self, message, arguments):
        """Base class for NodeGlobal exceptions"""
        Exception.__init__(self, message + ": {0}".format(arguments))
        self.ErrorMessage = message
        self.ErrorArguments = arguments
        pass


class WrongRoleSelected(NodeGlobalException):
    """Raised when a submitted server has no role requested"""
    pass

