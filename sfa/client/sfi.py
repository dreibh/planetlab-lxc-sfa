#! /usr/bin/env python

# sfi -- slice-based facility interface

import sys
import os, os.path
import tempfile
import traceback
from types import StringTypes, ListType
from optparse import OptionParser

from sfa.trust.certificate import Keypair, Certificate
from sfa.trust.credential import Credential

from sfa.util.geniclient import GeniClient
from sfa.util.record import *
from sfa.util.rspec import Rspec
from sfa.util.xmlrpcprotocol import ServerException
from sfa.util.config import Config

# xxx todo xxx auto-load ~/.sfi/sfi_config

sfi_dir = os.path.expanduser("~/.sfi/")
slicemgr = None
registry = None
user = None
authority = None
verbose = False

#
# Establish Connection to SliceMgr and Registry Servers
#
def set_servers(options):
   global slicemgr
   global registry
   global user
   global authority

   config_file = sfi_dir + os.sep + "sfi_config"
   try:
      config = Config (config_file)
   except:
      print "Failed to read configuration file",config_file
      print "Make sure to remove the export clauses and to add quotes"
      if not options.verbose:
         print "Re-run with -v for more details"
      else:
         traceback.print_exc()
      sys.exit(1)

   errors=0
   # Set SliceMgr URL
   if (options.sm is not None):
      sm_url = options.sm
   elif hasattr(config,"SFI_SM"):
      sm_url = config.SFI_SM
   else:
      print "You need to set e.g. SFI_SM='http://your.slicemanager.url:12347/' in %s"%config_file
      errors +=1 

   # Set Registry URL
   if (options.registry is not None):
      reg_url = options.registry
   elif hasattr(config,"SFI_REGISTRY"):
      reg_url = config.SFI_REGISTRY
   else:
      print "You need to set e.g. SFI_REGISTRY='http://your.registry.url:12345/' in %s"%config_file
      errors +=1 

   # Set user HRN
   if (options.user is not None):
      user = options.user
   elif hasattr(config,"SFI_USER"):
      user = config.SFI_USER
   else:
      print "You need to set e.g. SFI_USER='plc.princeton.username' in %s"%config_file
      errors +=1 

   # Set authority HRN
   if (options.auth is not None):
      authority = options.auth
   elif hasattr(config,"SFI_AUTH"):
      authority = config.SFI_AUTH
   else:
      print "You need to set e.g. SFI_AUTH='plc.princeton' in %s"%config_file
      errors +=1 

   if errors:
      sys.exit(1)

   if options.verbose :
      print "Contacting Slice Manager at:", sm_url
      print "Contacting Registry at:", reg_url

   # Get key and certificate
   key_file = get_key_file()
   cert_file = get_cert_file(key_file)

   # Establish connection to server(s)
   slicemgr = GeniClient(sm_url, key_file, cert_file, options.protocol)
   registry = GeniClient(reg_url, key_file, cert_file, options.protocol)
   return

#
# Get various credential and spec files
#
# Establishes limiting conventions
#   - conflates MAs and SAs
#   - assumes last token in slice name is unique
#
# Bootstraps credentials
#   - bootstrap user credential from self-signed certificate
#   - bootstrap authority credential from user credential
#   - bootstrap slice credential from user credential
#

def get_leaf(name):
   parts = name.split(".")
   return parts[-1]

def get_key_file():
   file = os.path.join(sfi_dir, get_leaf(user) + ".pkey")
   if (os.path.isfile(file)):
      return file
   else:
      print "Key file", file, "does not exist"
      sys.exit(-1)
   return

def get_cert_file(key_file):
   global verbose

   file = os.path.join(sfi_dir, get_leaf(user) + ".cert")
   if (os.path.isfile(file)):
      return file
   else:
      k = Keypair(filename = key_file)
      cert = Certificate(subject=user)
      cert.set_pubkey(k)
      cert.set_issuer(k, user)
      cert.sign()
      if verbose :
         print "Writing self-signed certificate to", file
      cert.save_to_file(file)
      return file

def get_user_cred():
   global user

   file = os.path.join(sfi_dir, get_leaf(user) + ".cred")
   if (os.path.isfile(file)):
      user_cred = Credential(filename=file)
      return user_cred
   else:
      # bootstrap user credential
      user_cred = registry.get_credential(None, "user", user)
      if user_cred:
         user_cred.save_to_file(file, save_parents=True)
         if verbose:
            print "Writing user credential to", file
         return user_cred
      else:
         print "Failed to get user credential"
         sys.exit(-1)

def get_auth_cred():
   global authority

   if not authority:
      print "no authority specified. Use -a or set SF_AUTH"
      sys.exit(-1)

   file = os.path.join(sfi_dir, get_leaf("authority") +".cred")
   if (os.path.isfile(file)):
      auth_cred = Credential(filename=file)
      return auth_cred
   else:
      # bootstrap authority credential from user credential
      user_cred = get_user_cred()
      auth_cred = registry.get_credential(user_cred, "sa", authority)
      if auth_cred:
         auth_cred.save_to_file(file, save_parents=True)
         if verbose:
            print "Writing authority credential to", file
         return auth_cred
      else:
         print "Failed to get authority credential"
         sys.exit(-1)

def get_slice_cred(name):
   file = os.path.join(sfi_dir, "slice_" + get_leaf(name) + ".cred")
   if (os.path.isfile(file)):
      slice_cred = Credential(filename=file)
      return slice_cred
   else:
      # bootstrap slice credential from user credential
      user_cred = get_user_cred()
      slice_cred = registry.get_credential(user_cred, "slice", name)
      if slice_cred:
         slice_cred.save_to_file(file, save_parents=True)
         if verbose:
            print "Writing slice credential to", file
         return slice_cred
      else:
         print "Failed to get slice credential"
         sys.exit(-1)

def delegate_cred(cred, hrn, type = 'authority'):
    # the gid and hrn of the object we are delegating
    object_gid = cred.get_gid_object()
    object_hrn = object_gid.get_hrn()
    cred.set_delegate(True)
    if not cred.get_delegate():
        raise Exception, "Error: Object credential %(object_hrn)s does not have delegate bit set" % locals()
       

    records = registry.resolve(cred, hrn)
    records = filter_records(type, records)
    
    if not records:
        raise Exception, "Error: Didn't find a %(type)s record for %(hrn)s" % locals()

    # the gid of the user who will be delegated too
    delegee_gid = records[0].get_gid_object()
    delegee_hrn = delegee_gid.get_hrn()
    
    # the key and hrn of the user who will be delegating
    user_key = Keypair(filename = get_key_file())
    user_hrn = cred.get_gid_caller().get_hrn()

    dcred = Credential(subject=object_hrn + " delegated to " + delegee_hrn)
    dcred.set_gid_caller(delegee_gid)
    dcred.set_gid_object(object_gid)
    dcred.set_privileges(cred.get_privileges())
    dcred.set_delegate(True)
    dcred.set_pubkey(object_gid.get_pubkey())
    dcred.set_issuer(user_key, user_hrn)
    dcred.set_parent(cred)
    dcred.encode()
    dcred.sign()

    return dcred

def get_rspec_file(rspec):
   if (os.path.isabs(rspec)):
      file = rspec
   else:
      file = os.path.join(sfi_dir, rspec)
   if (os.path.isfile(file)):
      return file
   else:
      print "No such rspec file", rspec
      sys.exit(1)

def get_record_file(record):
   if (os.path.isabs(record)):
      file = record
   else:
      file = os.path.join(sfi_dir, record)
   if (os.path.isfile(file)):
      return file
   else:
      print "No such registry record file", record
      sys.exit(1)

def load_publickey_string(fn):
   f = file(fn,"r")
   key_string = f.read()

   # if the filename is a private key file, then extract the public key
   if "PRIVATE KEY" in key_string:
       outfn = tempfile.mktemp()
       cmd = "openssl rsa -in " + fn + " -pubout -outform PEM -out " + outfn
       os.system(cmd)
       f = file(outfn, "r")
       key_string = f.read()
       os.remove(outfn)

   return key_string
#
# Generate sub-command parser
#
def create_cmd_parser(command, additional_cmdargs = None):
   cmdargs = {"list": "name",
              "show": "name",
              "remove": "name",
              "add": "record",
              "update": "record",
              "slices": "",
              "resources": "[name]",
              "create": "name rspec",
              "delete": "name",
              "reset": "name",
              "start": "name",
              "stop": "name",
              "delegate": "name"
             }

   if additional_cmdargs:
      cmdargs.update(additional_cmdargs)

   if command not in cmdargs:
      print "Invalid command\n"
      print "Commands: ",
      for key in cmdargs.keys():
          print key+",",
      print ""
      sys.exit(2)

   parser = OptionParser(usage="sfi [sfi_options] %s [options] %s" \
      % (command, cmdargs[command]))

   if command in ("resources"):
      parser.add_option("-f", "--format", dest="format",type="choice",
           help="display format (dns|ip|xml)",default="xml",
           choices=("dns","ip","xml"))
      
   if command in ("list", "show", "remove"):
      parser.add_option("-t", "--type", dest="type",type="choice",
           help="type filter (user|slice|sa|ma|node|aggregate)",
           choices=("user","slice","sa","ma","node","aggregate", "all"),
           default="all")
      
   if command in ("resources","show"):
      parser.add_option("-o", "--output", dest="file",
           help="output XML to file", metavar="FILE", default=None)

   if command in ("show", "list"):
        parser.add_option("-f", "--format", dest="format", type="choice",
           help="display format (text|xml)",default="text",
           choices=("text","xml"))
        
   if command in ("delegate"):
      parser.add_option("-u", "--user",
        action="store_true", dest="delegate_user", default=False,
        help="delegate user credential")
      parser.add_option("-s", "--slice", dest="delegate_slice",
        help="delegate slice credential", metavar="HRN", default=None)
   return parser

def create_parser():
   # Generate command line parser
   parser = OptionParser(usage="sfi [options] command [command_options] [command_args]",
        description="Commands: list,show,remove,add,update,nodes,slices,resources,create,delete,start,stop,reset")
   parser.add_option("-r", "--registry", dest="registry",
        help="root registry", metavar="URL", default=None)
   parser.add_option("-s", "--slicemgr", dest="sm",
        help="slice manager", metavar="URL", default=None)
   parser.add_option("-d", "--dir", dest="dir",
        help="working directory", metavar="PATH", default = sfi_dir)
   parser.add_option("-u", "--user", dest="user",
        help="user name", metavar="HRN", default=None)
   parser.add_option("-a", "--auth", dest="auth",
        help="authority name", metavar="HRN", default=None)
   parser.add_option("-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="verbose mode")
   parser.add_option("-p", "--protocol",
        dest="protocol", default="xmlrpc",
        help="RPC protocol (xmlrpc or soap)")
   parser.disable_interspersed_args()

   return parser

def dispatch(command, cmd_opts, cmd_args):
   globals()[command](cmd_opts, cmd_args)

#
# Main: parse arguments and dispatch to command
#
def main():
   global verbose

   parser = create_parser()
   (options, args) = parser.parse_args()

   if len(args) <= 0:
        print "No command given. Use -h for help."
        return -1

   command = args[0]
   (cmd_opts, cmd_args) = create_cmd_parser(command).parse_args(args[1:])
   verbose = options.verbose
   if verbose :
      print "Resgistry %s, sm %s, dir %s, user %s, auth %s" % (options.registry,
                                                               options.sm,
                                                               options.dir,
                                                               options.user,
                                                               options.auth)
      print "Command %s" %command
      if command in ("resources"):
         print "resources cmd_opts %s" %cmd_opts.format
      elif command in ("list","show","remove"):
         print "cmd_opts.type %s" %cmd_opts.type
      print "cmd_args %s" %cmd_args

   set_servers(options)

   try:
      dispatch(command, cmd_opts, cmd_args)
   except KeyError:
      raise 
      print "Command not found:", command
      sys.exit(1)

   return

#
# Following functions implement the commands
#
# Registry-related commands
#

# list entires in named authority registry
def list(opts, args):
   global registry
   user_cred = get_user_cred()
   try:
      list = registry.list(user_cred, args[0])
   except IndexError:
      raise Exception, "Not enough parameters for the 'list' command"
      
   # filter on person, slice, site, node, etc.  
   # THis really should be in the filter_records funct def comment...
   list = filter_records(opts.type, list)
   for record in list:
       print "%s (%s)" % (record['hrn'], record['type'])     
   if opts.file:
       save_records_to_file(opts.file, list)
   return

# show named registry record
def show(opts, args):
   global registry
   user_cred = get_user_cred()
   records = registry.resolve(user_cred, args[0])
   records = filter_records(opts.type, records)
   if not records:
      print "No record of type", opts.type
   for record in records:
       if record['type'] in ['user']:
           record = UserRecord(dict = record)
       elif record['type'] in ['slice']:
           record = SliceRecord(dict = record)
       elif record['type'] in ['node']:
           record = NodeRecord(dict = record)
       elif record['type'] in ['authority', 'ma', 'sa']:
           record = AuthorityRecord(dict = record)
       else:
           record = GeniRecord(dict = record)

       if (opts.format=="text"):
            record.dump() 
       else:
            print record.save_to_string()
   
   if opts.file:
       save_records_to_file(opts.file, records)
   return

def delegate(opts, args):
   global registry
   user_cred = get_user_cred()
   if opts.delegate_user:
       object_cred = user_cred
   elif opts.delegate_slice:
       object_cred = get_slice_cred(opts.delegate_slice)
   else:
       print "Must specify either --user or --slice <hrn>"
       return

   # the gid and hrn of the object we are delegating
   object_gid = object_cred.get_gid_object()
   object_hrn = object_gid.get_hrn()

   if not object_cred.get_delegate():
       print "Error: Object credential", object_hrn, "does not have delegate bit set"
       return

   records = registry.resolve(user_cred, args[0])
   records = filter_records("user", records)

   if not records:
       print "Error: Didn't find a user record for", args[0]
       return

   # the gid of the user who will be delegated too
   delegee_gid = records[0].get_gid_object()
   delegee_hrn = delegee_gid.get_hrn()

   # the key and hrn of the user who will be delegating
   user_key = Keypair(filename = get_key_file())
   user_hrn = user_cred.get_gid_caller().get_hrn()

   dcred = Credential(subject=object_hrn + " delegated to " + delegee_hrn)
   dcred.set_gid_caller(delegee_gid)
   dcred.set_gid_object(object_gid)
   dcred.set_privileges(object_cred.get_privileges())
   dcred.set_delegate(True)
   dcred.set_pubkey(object_gid.get_pubkey())
   dcred.set_issuer(user_key, user_hrn)
   dcred.set_parent(object_cred)
   dcred.encode()
   dcred.sign()

   if opts.delegate_user:
       dest_fn = os.path.join(sfi_dir, get_leaf(delegee_hrn) + "_" + get_leaf(object_hrn) + ".cred")
   elif opts.delegate_slice:
       dest_fn = os.path_join(sfi_dir, get_leaf(delegee_hrn) + "_slice_" + get_leaf(object_hrn) + ".cred")

   dcred.save_to_file(dest_fn, save_parents = True)

   print "delegated credential for", object_hrn, "to", delegee_hrn, "and wrote to", dest_fn

# removed named registry record
#   - have to first retrieve the record to be removed
def remove(opts, args):
   global registry
   auth_cred = get_auth_cred()
   return registry.remove(auth_cred, opts.type, args[0])

# add named registry record
def add(opts, args):
   global registry
   auth_cred = get_auth_cred()
   rec_file = get_record_file(args[0])
   record = load_record_from_file(rec_file)

   return registry.register(auth_cred, record)

# update named registry entry
def update(opts, args):
   global registry
   user_cred = get_user_cred()
   rec_file = get_record_file(args[0])
   record = load_record_from_file(rec_file)
   if record.get_type() == "user":
       if record.get_name() == user_cred.get_gid_object().get_hrn():
          cred = user_cred
       else:
          cred = get_auth_cred()
   elif record.get_type() in ["slice"]:
       try:
           cred = get_slice_cred(record.get_name())
       except ServerException, e:
           # XXX smbaker -- once we have better error return codes, update this
           # to do something better than a string compare
           if "Permission error" in e.args[0]:
               cred = get_auth_cred()
           else:
               raise
   elif record.get_type() in ["authority"]:
       cred = get_auth_cred()
   elif record.get_type() == 'node':
        cred = get_auth_cred()
   else:
       raise "unknown record type" + record.get_type()
   return registry.update(cred, record)

#
# Slice-related commands
#

# list available nodes -- now use 'resources' w/ no argument instead
#def nodes(opts, args):
#   global slicemgr
#   user_cred = get_user_cred() 
#   if not opts.format:
#      context = None
#   else:
#      context = opts.format
#   results = slicemgr.list_nodes(user_cred)
#   if opts.format in ['rspec']:     
#      display_rspec(results)
#   else:
#      display_list(results)
#   if (opts.file is not None):
#      rspec = slicemgr.list_nodes(user_cred)
#      save_rspec_to_file(rspec, opts.file)
#   return

# list instantiated slices
def slices(opts, args):
   global slicemgr
   user_cred = get_user_cred()
   results = slicemgr.get_slices(user_cred)
   display_list(results)
   return

# show rspec for named slice
def resources(opts, args):
   global slicemgr
   if args: 
       slice_cred = get_slice_cred(args[0])
       result = slicemgr.get_resources(slice_cred, args[0])
   else:
       user_cred = get_user_cred()
       result = slicemgr.get_resources(user_cred)
   format = opts.format      
   display_rspec(result, format)
   if (opts.file is not None):
      save_rspec_to_file(result, opts.file)
   return

# created named slice with given rspec
def create(opts, args):
   global slicemgr
   slice_hrn = args[0]
   slice_cred = get_slice_cred(slice_hrn)
   rspec_file = get_rspec_file(args[1])
   rspec=open(rspec_file).read()
   return slicemgr.create_slice(slice_cred, slice_hrn, rspec)

# delete named slice
def delete(opts, args):
   global slicemgr
   slice_hrn = args[0]
   slice_cred = get_slice_cred(slice_hrn)
   
   return slicemgr.delete_slice(slice_cred, slice_hrn)

# start named slice
def start(opts, args):
   global slicemgr
   slice_hrn = args[0]
   slice_cred = get_slice_cred(args[0])
   return slicemgr.start_slice(slice_cred, slice_hrn)

# stop named slice
def stop(opts, args):
   global slicemgr
   slice_hrn = args[0]
   slice_cred = get_slice_cred(args[0])
   return slicemgr.stop_slice(slice_cred, slice_hrn)

# reset named slice
def reset(opts, args):
   global slicemgr
   slice_hrn = args[0]
   slice_cred = get_slice_cred(args[0])
   return slicemgr.reset_slice(slice_cred, slice_hrn)

#
#
# Display, Save, and Filter RSpecs and Records
#   - to be replace by EMF-generated routines
#
#

def display_rspec(rspec, format = 'rspec'):
    if format in ['dns']:
        spec = Rspec()
        spec.parseString(rspec)
        hostnames = []
        nodespecs = spec.getDictsByTagName('NodeSpec')
        for nodespec in nodespecs:
            if nodespec.has_key('name') and nodespec['name']:
                if isinstance(nodespec['name'], ListType):
                    hostnames.extend(nodespec['name'])
                elif isinstance(nodespec['name'], StringTypes):
                    hostnames.append(nodespec['name'])
        result = hostnames
    elif format in ['ip']:
        spec = Rspec()
        spec.parseString(rspec)
        ips = []
        ifspecs = spec.getDictsByTagName('IfSpec')
        for ifspec in ifspecs:
            if ifspec.has_key('addr') and ifspec['addr']:
                ips.append(ifspec['addr'])
        result = ips 
    else:     
        result = rspec

    print result
    return

def display_list(results):
    for result in results:
        print result

def save_rspec_to_file(rspec, filename):
   if not filename.startswith(os.sep):
       filename = sfi_dir + filename
   if not filename.endswith(".rspec"):
       filename = filename + ".rspec"

   f = open(filename, 'w')
   f.write(rspec)
   f.close()
   return

def display_records(recordList, dump = False):
   ''' Print all fields in the record'''
   for record in recordList:
      display_record(record, dump)

def display_record(record, dump = False):
   if dump:
       record.dump()
   else:
       info = record.getdict()
       print "%s (%s)" % (info['hrn'], info['type'])
   return

def filter_records(type, records):
   filtered_records = []
   for record in records:
       if (record.get_type() == type) or (type == "all"):
           filtered_records.append(record)
   return filtered_records

def save_records_to_file(filename, recordList):
   index = 0
   for record in recordList:
       if index>0:
           save_record_to_file(filename + "." + str(index), record)
       else:
           save_record_to_file(filename, record)
       index = index + 1

def save_record_to_file(filename, record):
   if not filename.startswith(os.sep):
       filename = sfi_dir + filename
   str = record.save_to_string()
   file(filename, "w").write(str)
   return

def load_record_from_file(filename):
   str = file(filename, "r").read()
   record = GeniRecord(string=str)
   return record

if __name__=="__main__":
   main()
