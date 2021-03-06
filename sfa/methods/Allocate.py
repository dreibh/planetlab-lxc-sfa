from sfa.util.faults import SfaInvalidArgument, InvalidRSpec, SfatablesRejected
from sfa.util.sfatime import datetime_to_string
from sfa.util.xrn import Xrn, urn_to_hrn
from sfa.util.method import Method
from sfa.util.sfatablesRuntime import run_sfatables
from sfa.trust.credential import Credential
from sfa.storage.parameter import Parameter, Mixed
from sfa.rspecs.rspec import RSpec
from sfa.util.sfalogging import logger


class Allocate(Method):
    """
    Allocate resources as described in a request RSpec argument
    to a slice with the named URN. On success, one or more slivers
    are allocated, containing resources satisfying the request, and
    assigned to the given slice. This method returns a listing and
    description of the resources reserved for the slice by this
    operation, in the form of a manifest RSpec. Allocated slivers
    are held for an aggregate-determined period. Clients must Renew
    or Provision slivers before the expiration time (given in the
    return struct), or the aggregate will automatically Delete them.

    @param slice_urn (string) URN of slice to allocate to
    @param credentials (dict) of credentials
    @param rspec (string) rspec to allocate
    @param options (dict)

    As of 3.1.16, the PL driver implements here an important option named
    'pltags' that affects the management of slice tags.

    This option can take 3 values
      (*) options['pltags'] == 'ignore' (default)
          This is the recommended mode; in this mode all slice tags passed
          here are ignore, which correspond to the <planetlab:attribute> XML tags in
          the <sliver_type> areas of incoming rspec to Allocate.
          In other words you are guaranteed to leave slice tags alone.
      (*) options['pltags'] == 'append'
          All incoming slice tags are added to corresponding slivers,
          unless an exact match can be found in the PLC db
      (*) options['pltags'] == 'sync'
          The historical mode, that attempts to leave the PLC db in a state
          in sync with the ones specified in incoming rspec.

    See also http://svn.planet-lab.org/wiki/SFASliceTags

    """
    interfaces = ['aggregate']
    accepts = [
        Parameter(str, "Slice URN"),
        Parameter(type([dict]), "List of credentials"),
        Parameter(str, "RSpec"),
        Parameter(dict, "options"),
    ]
    returns = Parameter(str, "Allocated RSpec")

    def call(self, xrn, creds, rspec, options):
        xrn = Xrn(xrn, type='slice')

        # Find the valid credentials
        valid_creds = self.api.auth.checkCredentialsSpeaksFor(
            creds, 'createsliver', xrn.get_hrn(), options=options)
        the_credential = Credential(cred=valid_creds[0])

        # use the expiration from the first valid credential to determine when
        # the slivers should expire.
        expiration = datetime_to_string(the_credential.expiration)

        logger.debug(
            "Allocate, received expiration from credential: %s" % expiration)

# turned off, as passing an empty rspec is indeed useful for cleaning up the slice
#        # make sure request is not empty
#        slivers = RSpec(rspec).version.get_nodes_with_slivers()
#        if not slivers:
#            raise InvalidRSpec("Missing <sliver_type> or <sliver> element. Request rspec must explicitly allocate slivers")

        # flter rspec through sfatables
        if self.api.interface in ['aggregate']:
            chain_name = 'INCOMING'
        logger.debug("Allocate: sfatables on chain %s" % chain_name)
        actual_caller_hrn = the_credential.actual_caller_hrn()
        logger.info("interface: %s\tcaller-hrn: %s\ttarget-hrn: %s\tmethod-name: %s" %
                    (self.api.interface, actual_caller_hrn, xrn.get_hrn(), self.name))
        rspec = run_sfatables(chain_name, xrn.get_hrn(),
                              actual_caller_hrn, rspec)
# turned off, as passing an empty rspec is indeed useful for cleaning up the slice
#        slivers = RSpec(rspec).version.get_nodes_with_slivers()
#        if not slivers:
#            raise SfatablesRejected(slice_xrn)

        # pass this to the driver code in case they need it
        options['actual_caller_hrn'] = actual_caller_hrn
        result = self.api.manager.Allocate(
            self.api, xrn.get_urn(), creds, rspec, expiration, options)
        return result
