### $Id: get_credential.py 15321 2009-10-15 05:01:21Z tmack $
### $URL: https://svn.planet-lab.org/svn/sfa/trunk/sfa/methods/get_credential.py $

from sfa.trust.credential import *
from sfa.trust.rights import *
from sfa.util.faults import *
from sfa.util.method import Method
from sfa.util.parameter import Parameter, Mixed
from sfa.util.record import GeniRecord
from sfa.util.debug import log

class get_self_credential(Method):
    """
    Retrive a credential for an object
    @param cert certificate string 
    @param type type of object (user | slice | sa | ma | node)
    @param hrn human readable name of object

    @return the string representation of a credential object  
    """

    interfaces = ['registry']
    
    accepts = [
        Parameter(str, "certificate"),
        Parameter(str, "Human readable name (hrn)"),
        Mixed(Parameter(str, "Request hash"),
              Parameter(None, "Request hash not specified"))
        ]

    returns = Parameter(str, "String representation of a credential object")

    def call(self, cert, type, hrn, request_hash=None):
        """
        get_self_credential a degenerate version of get_credential used by a client
        to get his initial credential when de doesnt have one. This is the same as
        get_credetial(..., cred = None, ...)

        The registry ensures that the client is the principal that is named by
        (type, name) by comparing the public key in the record's  GID to the
        private key used to encrypt the client side of the HTTPS connection. Thus
        it is impossible for one principal to retrive another principal's
        credential without having the appropriate private key.

        @param type type of object (user | slice | sa | ma | node)
        @param hrn human readable name of authority to list
        @return string representation of a credential object
        """
        self.api.auth.verify_object_belongs_to_me(hrn)
        
        # send the call to the right manager
        manager_base = 'sfa.managers'
        mgr_type = self.api.config.SFA_REGISTRY_TYPE
        manager_module = manager_base + ".registry_manager_%s" % mgr_type
        manager = __import__(manager_module, fromlist=[manager_base])

        # authenticate the gid
        records = manager.resolve(self.api, hrn, type)
        if not records:
            raise RecordNotFound(hrn)
        record = GeniRecord(dict=records[0])
        gid = record.get_gid_object()
        gid_str = gid.save_to_string(save_parents=True)
        self.api.auth.authenticateGid(gid_str, [cert, type, hrn], request_hash)
        # authenticate the certificate against the gid in the db
        certificate = Certificate(string=cert)
        if not certificate.is_pubkey(gid.get_pubkey()):
            raise ConnectionKeyGIDMismatch(gid.get_subject())
        
        return manager.get_credential(self.api, hrn, type, is_self=True)
