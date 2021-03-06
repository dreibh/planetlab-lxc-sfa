
from sfa.util.xrn import urn_to_hrn
from sfa.util.method import Method
from sfa.util.sfalogging import logger

from sfa.storage.parameter import Parameter, Mixed
from sfa.trust.credential import Credential


class CreateGid(Method):
    """
    Create a signed credential for the object with the registry. In addition to being stored in the
    SFA database, the appropriate records will also be created in the
    PLC databases

    @param cred credential string
    @param xrn urn or hrn of certificate owner
    @param cert caller's certificate

    @return gid string representation
    """

    interfaces = ['registry']

    accepts = [
        Mixed(Parameter(str, "Credential string"),
              Parameter(type([str]), "List of credentials")),
        Parameter(str, "URN or HRN of certificate owner"),
        Parameter(str, "Certificate string"),
    ]

    returns = Parameter(int, "String representation of gid object")

    def call(self, creds, xrn, cert=None):
        # TODO: is there a better right to check for or is 'update good enough?
        valid_creds = self.api.auth.checkCredentials(creds, 'update')

        # verify permissions
        hrn, type = urn_to_hrn(xrn)
        self.api.auth.verify_object_permission(hrn)

        # log the call
        origin_hrn = Credential(
            string=valid_creds[0]).get_gid_caller().get_hrn()
        logger.info("interface: %s\tcaller-hrn: %s\ttarget-hrn: %s\tmethod-name: %s" %
                    (self.api.interface, origin_hrn, xrn, self.name))

        return self.api.manager.CreateGid(self.api, xrn, cert)
