##
# GENI PLC Wrapper
#
# This wrapper implements the Geni Registry and Slice Interfaces on PLC.
# Depending on command line options, it starts some combination of a
# Registry, an Aggregate Manager, and a Slice Manager.
#
# There are several items that need to be done before starting the wrapper
# server.
#
# NOTE:  Many configuration settings, including the PLC maintenance account
# credentials, URI of the PLCAPI, and PLC DB URI and admin credentials are initialized
# from your MyPLC configuration (/etc/planetlab/plc_config*).  Please make sure this information
# is up to date and accurate.
#
# 1) Import the existing planetlab database, creating the
#    appropriate geni records. This is done by running the "gimport.py" tool.
#
# 2) Create a "trusted_roots" directory and place the certificate of the root
#    authority in that directory. Given the defaults in gimport.py, this
#    certificate would be named "planetlab.gid". For example,
#
#    mkdir trusted_roots; cp authorities/planetlab.gid trusted_roots/
#
# TODO: Can all three servers use the same "registry" certificate?
##

# TCP ports for the three servers
registry_port=12345
aggregate_port=12346
slicemgr_port=12347

import os, os.path
from optparse import OptionParser

from geni.util.hierarchy import Hierarchy
from geni.util.trustedroot import TrustedRootList
from geni.util.cert import Keypair, Certificate
from geni.registry import Registry
from geni.aggregate import Aggregate
from geni.slicemgr import SliceMgr

def main():
    global AuthHierarchy
    global TrustedRoots
    global registry_port
    global aggregate_port
    global slicemgr_port

    # Generate command line parser
    parser = OptionParser(usage="plc [options]")
    parser.add_option("-r", "--registry", dest="registry", action="store_true",
         help="run registry server", default=False)
    parser.add_option("-s", "--slicemgr", dest="sm", action="store_true",
         help="run slice manager", default=False)
    parser.add_option("-a", "--aggregate", dest="am", action="store_true",
         help="run aggregate manager", default=False)
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", 
         help="verbose mode", default=False)
    (options, args) = parser.parse_args()
 
    key_file = "server.key"
    cert_file = "server.cert"

    if (os.path.exists(key_file)) and (not os.path.exists(cert_file)):
        # If private key exists and cert doesnt, recreate cert
        key = Keypair(filename=key_file)
        cert = Certificate(subject="registry")
        cert.set_issuer(key=key, subject="registry")
        cert.set_pubkey(key)
        cert.sign()
        cert.save_to_file(cert_file)

    elif (not os.path.exists(key_file)) or (not os.path.exists(cert_file)):
        # if no key is specified, then make one up
        key = Keypair(create=True)
        key.save_to_file(key_file)
        cert = Certificate(subject="registry")
        cert.set_issuer(key=key, subject="registry")
        cert.set_pubkey(key)
        cert.sign()
        cert.save_to_file(cert_file)

    AuthHierarchy = Hierarchy()

    TrustedRoots = TrustedRootList()

    # start registry server
    if (options.registry):
        r = Registry("", registry_port, key_file, cert_file)
        r.trusted_cert_list = TrustedRoots.get_list()
        r.hierarchy = AuthHierarchy
        r.start()

    # start aggregate manager
    if (options.am):
        a = Aggregate("", aggregate_port, key_file, cert_file)
        a.trusted_cert_list = TrustedRoots.get_list()
        a.start()

    # start slice manager
    if (options.sm):
        s = SliceMgr("", slicemgr_port, key_file, cert_file)
        s.trusted_cert_list = TrustedRoots.get_list()
        s.start()

if __name__ == "__main__":
    main()
