from types import ModuleType

from sfa.util.faults import SfaNotImplemented, SfaAPIError
from sfa.util.sfalogging import logger

####################


class ManagerWrapper:
    """
    This class acts as a wrapper around an SFA interface manager module, but
    can be used with any python module. The purpose of this class is raise a
    SfaNotImplemented exception if someone attempts to use an attribute
    (could be a callable) thats not available in the library by checking the
    library using hasattr. This helps to communicate better errors messages
    to the users and developers in the event that a specifiec operation
    is not implemented by a libarary and will generally be more helpful than
    the standard AttributeError
    """

    def __init__(self, manager, interface, config):
        if isinstance(manager, ModuleType):
            # old-fashioned module implementation
            self.manager = manager
        # if it's a class
        elif isinstance(manager, type):
            # create an instance; we don't pass the api in argument as it is passed
            # to the actual method calls anyway
            self.manager = manager(config)
        else:
            # that's what happens when there's something wrong with the db
            # or any bad stuff of that kind at startup time
            logger.log_exc(
                "Failed to create a manager, startup sequence is broken")
            raise SfaAPIError(
                "Argument to ManagerWrapper must be a module or class")
        self.interface = interface

    def __getattr__(self, method):
        if not hasattr(self.manager, method):
            raise SfaNotImplemented(self.interface, method)
        return getattr(self.manager, method)
