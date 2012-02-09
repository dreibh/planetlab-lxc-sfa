from sfa.util.sfalogging import logger
from sfa.util.faults import SfaFault

# this is probably too big to swallow but for a starting point..
from sfa.plc.pldriver import PlDriver

from sfa.federica.fdshell import FdShell

# hardwired for now
# this could/should be obtained by issuing getRSpecVersion
federica_version_string="RSpecV2"

class FdDriver (PlDriver):

    def __init__ (self,config): 
        PlDriver.__init__ (self, config)
        self.shell=FdShell(config)

    # the agreement with the federica driver is for them to expose results in a way
    # compliant with the avpi v2 return code, i.e. a dict with 'code' 'value' 'output'
    # essentially, either 'code'==0, then 'value' is set to the actual result
    # otherwise, 'code' is set to an error code and 'output' holds an error message
    def response (self, from_xmlrpc):
        if isinstance (from_xmlrpc, dict) and 'code' in from_xmlrpc:
            if from_xmlrpc['code']==0:
                return from_xmlrpc['value']
            else:
                raise SfaFault(from_xmlrpc['code'],from_xmlrpc['output'])
        else:
            logger.warning("unexpected result from federica xmlrpc api")
            return from_xmlrpc

    def aggregate_version (self):
        return { 'federica_version_string' : federica_version_string, }

    def testbed_name (self):
        return "federica"

    def list_slices (self, creds, options):
        return self.response(self.shell.listSlices())

    def sliver_status (self, slice_urn, slice_hrn):
        return "fddriver.sliver_status: undefined/todo for slice %s"%slice_hrn

    def list_resources (self, slice_urn, slice_hrn, creds, options):
        # right now rspec_version is ignored on the federica side
        # we normally derive it from options
        # look in cache if client has requested so
        cached_requested = options.get('cached', True) 
        # global advertisement
        if not slice_hrn:
            # self.cache is initialized unless the global config has it turned off
            if cached_requested and self.cache:
                # using federica_version_string as the key into the cache
                rspec = self.cache.get(federica_version_string)
                if rspec:
                    logger.debug("FdDriver.ListResources: returning cached advertisement")
                    return self.response(rspec)
            # otherwise, need to get it
            rspec = self.shell.listAvailableResources (federica_version_string)
            # cache it for future use
            if self.cache:
                logger.debug("FdDriver.ListResources: stores advertisement in cache")
                self.cache.add(federica_version_string, rspec)
            return self.response(rspec)
        # about a given slice : don't cache
        else:
# that's what the final version would look like
            return self.response(self.shell.listSliceResources(federica_version_string, slice_urn))
# # just to see how the ad shows up in sface
# # caching it for convenience as it's the ad anyways
#             if cached_requested and self.cache:
#                 rspec = self.cache.get(federica_version_string)
#                 if rspec:
#                     logger.debug("FdDriver.ListResources: returning cached advertisement")
#                     return rspec 
#             
#             return self.shell.listAvailableResources(federica_version_string)

#String createSlice(String credentials, String sliceUrn, String rspecVersion, String rspecString):
    def create_sliver (self, slice_urn, slice_hrn, creds, rspec_string, users, options):
        # right now version_string is ignored on the federica side
        # we normally derive it from options
        return self.response(self.shell.createSlice(creds, slice_urn, federica_version_string, rspec_string))

#String deleteSlice(String credentials, String sliceUrn):
    def delete_sliver (self, slice_urn, slice_hrn, creds, options):
        # right now version_string is ignored on the federica side
        # we normally derive it from options
        # xxx not sure if that's currentl supported at all
        return self.response(self.shell.deleteSlice(creds, slice_urn))

    # for the the following methods we use what is provided by the default driver class
    #def renew_sliver (self, slice_urn, slice_hrn, creds, expiration_time, options):
    #def start_slice (self, slice_urn, slice_xrn, creds):
    #def stop_slice (self, slice_urn, slice_xrn, creds):
    #def reset_slice (self, slice_urn, slice_xrn, creds):
    #def get_ticket (self, slice_urn, slice_xrn, creds, rspec, options):
