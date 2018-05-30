from sfa.util.method import Method
from sfa.util.sfalogging import logger

from sfa.storage.parameter import Parameter


class GetVersion(Method):
    """
    Returns this GENI Aggregate Manager's Version Information
    @return version
    """
    interfaces = ['registry', 'aggregate', 'component']
    accepts = [
        Parameter(dict, "Options")
    ]
    returns = Parameter(dict, "Version information")

    # API v2 specifies options is optional, so..
    def call(self, options=None):
        if options is None:
            options = {}
        logger.info("interface: %s\tmethod-name: %s" %
                    (self.api.interface, self.name))
        return self.api.manager.GetVersion(self.api, options)
