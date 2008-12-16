##
# Import PLC records into the Geni database. It is indended that this tool be
# run once to create Geni records that reflect the current state of the
# planetlab database.
#
# The import tool assumes that the existing PLC hierarchy should all be part
# of "planetlab.us" (see the root_auth and level1_auth variables below).
#
# Public keys are extracted from the users' SSH keys automatically and used to
# create GIDs. This is relatively experimental as a custom tool had to be
# written to perform conversion from SSH to OpenSSL format. It only supports
# RSA keys at this time, not DSA keys.
##

import getopt
import sys
import tempfile

from cert import *
from trustedroot import *
from hierarchy import *
from record import *
from genitable import *
from misc import *

shell = None

##
# Two authorities are specified: the root authority and the level1 authority.

root_auth = "planetlab"
level1_auth = "planetlab"


def un_unicode(str):
   if isinstance(str, unicode):
       return str.encode("ascii", "ignore")
   else:
       return str

def cleanup_string(str):
    # pgsql has a fit with strings that have high ascii in them, so filter it
    # out when generating the hrns.
    tmp = ""
    for c in str:
        if ord(c) < 128:
            tmp = tmp + c
    str = tmp

    str = un_unicode(str)
    str = str.replace(" ", "_")
    str = str.replace(".", "_")
    str = str.replace("(", "_")
    str = str.replace("'", "_")
    str = str.replace(")", "_")
    str = str.replace('"', "_")
    return str

def process_options():
   global hrn

   (options, args) = getopt.getopt(sys.argv[1:], '', [])
   for opt in options:
       name = opt[0]
       val = opt[1]

def connect_shell():
    global pl_auth, shell

    # get PL account settings from config module
    pl_auth = get_pl_auth()

    # connect to planetlab
    if "Url" in pl_auth:
        import remoteshell
        shell = remoteshell.RemoteShell()
    else:
        import PLC.Shell
        shell = PLC.Shell.Shell(globals = globals())

def get_auth_table(auth_name):
    AuthHierarchy = Hierarchy()
    auth_info = AuthHierarchy.get_auth_info(auth_name)

    table = GeniTable(hrn=auth_name,
                      cninfo=auth_info.get_dbinfo())

    # if the table doesn't exist, then it means we haven't put any records
    # into this authority yet.

    if not table.exists():
        report.trace("Import: creating table for authority " + auth_name)
        table.create()

    return table

def get_pl_pubkey(key_id):
    keys = shell.GetKeys(pl_auth, [key_id])
    if keys:
        key_str = keys[0]['key']

        if "ssh-dss" in key_str:
            print "XXX: DSA key encountered, ignoring"
            return None

        # generate temporary files to hold the keys
        (ssh_f, ssh_fn) = tempfile.mkstemp()
        ssl_fn = tempfile.mktemp()

        os.write(ssh_f, key_str)
        os.close(ssh_f)

        cmd = "../keyconvert/keyconvert " + ssh_fn + " " + ssl_fn
        print cmd
        os.system(cmd)

        # this check leaves the temporary file containing the public key so
        # that it can be expected to see why it failed.
        # TODO: for production, cleanup the temporary files
        if not os.path.exists(ssl_fn):
            report.trace("  failed to convert key from " + ssh_fn + " to " + ssl_fn)
            return None

        k = Keypair()
        try:
            k.load_pubkey_from_file(ssl_fn)
        except:
            print "XXX: Error while converting key: ", key_str
            k = None

        # remove the temporary files
        os.remove(ssh_fn)
        os.remove(ssl_fn)

        return k
    else:
        return None

def person_to_hrn(parent_hrn, person):
    personname = person['last_name'] + "_" + person['first_name']

    personname = cleanup_string(personname)

    hrn = parent_hrn + "." + personname
    return hrn

def import_person(parent_hrn, person):
    AuthHierarchy = Hierarchy()
    hrn = person_to_hrn(parent_hrn, person)

    # ASN.1 will have problems with hrn's longer than 64 characters
    if len(hrn) > 64:
        hrn = hrn[:64]

    report.trace("Import: importing person " + hrn)

    table = get_auth_table(parent_hrn)

    person_record = table.resolve("user", hrn)
    if not person_record:
        key_ids = person["key_ids"]

        if key_ids:
            # get the user's private key from the SSH keys they have uploaded
            # to planetlab
            pkey = get_pl_pubkey(key_ids[0])
        else:
            # the user has no keys
            report.trace("   person " + hrn + " does not have a PL public key")
            pkey = None

        # if a key is unavailable, then we still need to put something in the
        # user's GID. So make one up.
        if not pkey:
            pkey = Keypair(create=True)

        person_gid = AuthHierarchy.create_gid(hrn, create_uuid(), pkey)
        person_record = GeniRecord(name=hrn, gid=person_gid, type="user", pointer=person['person_id'])
        report.trace("  inserting user record for " + hrn)
        table.insert(person_record)
    else:
	key_ids = person["key_ids"]
	if key_ids:
	    pkey = get_pl_pubkey(key_ids[0])
	    person_gid = AuthHierarchy.create_gid(hrn, create_uuid(), pkey)
            person_record = GeniRecord(name=hrn, gid=person_gid, type="user", pointer=person['person_id'])
            report.trace("  updating user record for " + hrn)
            table.update(person_record)
	    
def import_slice(parent_hrn, slice):
    AuthHierarchy = Hierarchy()
    slicename = slice['name'].split("_",1)[-1]
    slicename = cleanup_string(slicename)

    if not slicename:
        report.error("Import_Slice: failed to parse slice name " + slice['name'])
        return

    hrn = parent_hrn + "." + slicename
    report.trace("Import: importing slice " + hrn)

    table = get_auth_table(parent_hrn)

    slice_record = table.resolve("slice", hrn)
    if not slice_record:
        pkey = Keypair(create=True)
        slice_gid = AuthHierarchy.create_gid(hrn, create_uuid(), pkey)
        slice_record = GeniRecord(name=hrn, gid=slice_gid, type="slice", pointer=slice['slice_id'])
        report.trace("  inserting slice record for " + hrn)
        table.insert(slice_record)

def import_node(parent_hrn, node):
    AuthHierarchy = Hierarchy()
    nodename = node['hostname']
    nodename = cleanup_string(nodename)

    if not nodename:
        report.error("Import_node: failed to parse node name " + node['hostname'])
        return

    hrn = parent_hrn + "." + nodename

    # ASN.1 will have problems with hrn's longer than 64 characters
    if len(hrn) > 64:
        hrn = hrn[:64]

    report.trace("Import: importing node " + hrn)

    table = get_auth_table(parent_hrn)

    node_record = table.resolve("node", hrn)
    if not node_record:
        pkey = Keypair(create=True)
        node_gid = AuthHierarchy.create_gid(hrn, create_uuid(), pkey)
        node_record = GeniRecord(name=hrn, gid=node_gid, type="node", pointer=node['node_id'])
        report.trace("  inserting node record for " + hrn)
        table.insert(node_record)

def import_site(parent_hrn, site):
    AuthHierarchy = Hierarchy()
    sitename = site['login_base']
    sitename = cleanup_string(sitename)

    hrn = parent_hrn + "." + sitename

    report.trace("Import_Site: importing site " + hrn)

    # create the authority
    if not AuthHierarchy.auth_exists(hrn):
        AuthHierarchy.create_auth(hrn)

    auth_info = AuthHierarchy.get_auth_info(hrn)

    table = get_auth_table(parent_hrn)

    sa_record = table.resolve("sa", hrn)
    if not sa_record:
        sa_record = GeniRecord(name=hrn, gid=auth_info.get_gid_object(), type="sa", pointer=site['site_id'])
        report.trace("  inserting sa record for " + hrn)
        table.insert(sa_record)

    ma_record = table.resolve("ma", hrn)
    if not ma_record:
        ma_record = GeniRecord(name=hrn, gid=auth_info.get_gid_object(), type="ma", pointer=site['site_id'])
        report.trace("  inserting ma record for " + hrn)
        table.insert(ma_record)

    for person_id in site['person_ids']:
        persons = shell.GetPersons(pl_auth, [person_id])
        if persons:
            import_person(hrn, persons[0])

    for slice_id in site['slice_ids']:
        slices = shell.GetSlices(pl_auth, [slice_id])
        if slices:
            import_slice(hrn, slices[0])

    for node_id in site['node_ids']:
        nodes = shell.GetNodes(pl_auth, [node_id])
        if nodes:
            import_node(hrn, nodes[0])

def create_top_level_auth_records(hrn):
    parent_hrn = get_authority(hrn)
    print hrn, ":", parent_hrn	
    auth_info = AuthHierarchy.get_auth_info(parent_hrn)
    table = get_auth_table(parent_hrn)

    sa_record = table.resolve("sa", hrn)
    if not sa_record:
        sa_record = GeniRecord(name=hrn, gid=auth_info.get_gid_object(), type="sa", pointer=-1)
        report.trace("  inserting sa record for " + hrn)
        table.insert(sa_record)

    ma_record = table.resolve("ma", hrn)
    if not ma_record:
        ma_record = GeniRecord(name=hrn, gid=auth_info.get_gid_object(), type="ma", pointer=-1)
        report.trace("  inserting ma record for " + hrn)
        table.insert(ma_record)

def main():
    global AuthHierarchy
    global TrustedRoots

    process_options()

    AuthHierarchy = Hierarchy()
    TrustedRoots = TrustedRootList()

    print "Import: creating top level authorities"

    if not AuthHierarchy.auth_exists(root_auth):
        AuthHierarchy.create_auth(root_auth)
    #create_top_level_auth_records(root_auth)
    if not AuthHierarchy.auth_exists(level1_auth):
        AuthHierarchy.create_auth(level1_auth)
    create_top_level_auth_records(level1_auth)

    print "Import: adding", root_auth, "to trusted list"
    root = AuthHierarchy.get_auth_info(root_auth)
    TrustedRoots.add_gid(root.get_gid_object())

    connect_shell()

    sites = shell.GetSites(pl_auth)
    for site in sites:
        import_site(level1_auth, site)

if __name__ == "__main__":
    main()
