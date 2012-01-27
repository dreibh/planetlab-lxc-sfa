import os

from sfa.util.config import Config
from sfa.util.xrn import Xrn, get_leaf, get_authority, hrn_to_urn
from sfa.util.plxrn import hostname_to_hrn, slicename_to_hrn, email_to_hrn, hrn_to_pl_slicename

from sfa.trust.gid import create_uuid    
from sfa.trust.certificate import convert_public_key, Keypair

from sfa.storage.alchemy import dbsession
from sfa.storage.model import RegRecord, RegAuthority, RegUser, RegSlice, RegNode

from sfa.plc.plshell import PlShell    

def load_keys(filename):
    keys = {}
    tmp_dict = {}
    try:
        execfile(filename, tmp_dict)
        if 'keys' in tmp_dict:
            keys = tmp_dict['keys']
        return keys
    except:
        return keys

def save_keys(filename, keys):
    f = open(filename, 'w')
    f.write("keys = %s" % str(keys))
    f.close()

def _get_site_hrn(interface_hrn, site):
    # Hardcode 'internet2' into the hrn for sites hosting
    # internet2 nodes. This is a special operation for some vini
    # sites only
    hrn = ".".join([interface_hrn, site['login_base']]) 
    if ".vini" in interface_hrn and interface_hrn.endswith('vini'):
        if site['login_base'].startswith("i2") or site['login_base'].startswith("nlr"):
            hrn = ".".join([interface_hrn, "internet2", site['login_base']])
    return hrn


class PlImporter:

    def __init__ (self, auth_hierarchy, logger):
        self.auth_hierarchy = auth_hierarchy
        self.logger=logger

    def record_options (self, parser):
        self.logger.debug ("PlImporter no options yet")
        pass

    def run (self, options):
        # we don't have any options for now
        self.logger.info ("PlImporter.run : to do")

        config = Config ()
        interface_hrn = config.SFA_INTERFACE_HRN
        root_auth = config.SFA_REGISTRY_ROOT_AUTH
        shell = PlShell (config)

        # create dict of all existing sfa records
        existing_records = {}
        existing_hrns = []
        key_ids = []
        for record in dbsession.query(RegRecord):
            existing_records[ (record.hrn, record.type,) ] = record
            existing_hrns.append(record.hrn) 
            
        # Get all plc sites
        sites = shell.GetSites({'peer_id': None})
        sites_dict = {}
        for site in sites:
            sites_dict[site['login_base']] = site 
    
        # Get all plc users
        persons = shell.GetPersons({'peer_id': None, 'enabled': True}, 
                                   ['person_id', 'email', 'key_ids', 'site_ids'])
        persons_dict = {}
        for person in persons:
            persons_dict[person['person_id']] = person
            key_ids.extend(person['key_ids'])

        # Get all public keys
        keys = shell.GetKeys( {'peer_id': None, 'key_id': key_ids})
        keys_dict = {}
        for key in keys:
            keys_dict[key['key_id']] = key['key']

        # create a dict of person keys keyed on key_id 
        keys_filename = config.config_path + os.sep + 'person_keys.py' 
        old_person_keys = load_keys(keys_filename)
        person_keys = {} 
        for person in persons:
            pubkeys = []
            for key_id in person['key_ids']:
                pubkeys.append(keys_dict[key_id])
            person_keys[person['person_id']] = pubkeys

        # Get all plc nodes  
        nodes = shell.GetNodes( {'peer_id': None}, ['node_id', 'hostname', 'site_id'])
        nodes_dict = {}
        for node in nodes:
            nodes_dict[node['node_id']] = node

        # Get all plc slices
        slices = shell.GetSlices( {'peer_id': None}, ['slice_id', 'name'])
        slices_dict = {}
        for slice in slices:
            slices_dict[slice['slice_id']] = slice

        # special case for vini
        if ".vini" in interface_hrn and interface_hrn.endswith('vini'):
            # create a fake internet2 site first
            i2site = {'name': 'Internet2', 'abbreviated_name': 'I2',
                        'login_base': 'internet2', 'site_id': -1}
            site_hrn = _get_site_hrn(interface_hrn, i2site)
            # import if hrn is not in list of existing hrns or if the hrn exists
            # but its not a site record
            if site_hrn not in existing_hrns or \
               (site_hrn, 'authority') not in existing_records:
                urn = hrn_to_urn(site_hrn, 'authority')
                if not self.auth_hierarchy.auth_exists(urn):
                    self.auth_hierarchy.create_auth(urn)
                auth_info = self.auth_hierarchy.get_auth_info(urn)
                auth_record = RegAuthority()
                auth_record.type='authority'
                auth_record.hrn=site_hrn
                auth_record.gid=auth_info.get_gid_object()
                auth_record.pointer=site['site_id']
                auth_record.authority=get_authority(site_hrn)
                dbsession.add(auth_record)
                dbsession.commit()
                self.logger.info("Import: Imported authority (vini site) %s"%auth_record)

        # start importing 
        for site in sites:
            site_hrn = _get_site_hrn(interface_hrn, site)
    
            # import if hrn is not in list of existing hrns or if the hrn exists
            # but its not a site record
            if site_hrn not in existing_hrns or \
               (site_hrn, 'authority') not in existing_records:
                try:
                    urn = hrn_to_urn(site_hrn, 'authority')
                    if not self.auth_hierarchy.auth_exists(urn):
                        self.auth_hierarchy.create_auth(urn)
                    auth_info = self.auth_hierarchy.get_auth_info(urn)
                    auth_record = RegAuthority()
                    auth_record.type='authority'
                    auth_record.hrn=site_hrn
                    auth_record.gid=auth_info.get_gid_object()
                    auth_record.pointer=site['site_id']
                    auth_record.authority=get_authority(site_hrn)
                    dbsession.add(auth_record)
                    dbsession.commit()
                    self.logger.info("Import: imported authority (site) : %s" % auth_record)  
                except:
                    # if the site import fails then there is no point in trying to import the
                    # site's child records (node, slices, persons), so skip them.
                    self.logger.log_exc("Import: failed to import site. Skipping child records") 
                    continue 
             
            # import node records
            for node_id in site['node_ids']:
                if node_id not in nodes_dict:
                    continue 
                node = nodes_dict[node_id]
                site_auth = get_authority(site_hrn)
                site_name = get_leaf(site_hrn)
                hrn =  hostname_to_hrn(site_auth, site_name, node['hostname'])
                if len(hrn) > 64:
                    hrn = hrn[:64]
                if hrn not in existing_hrns or \
                   (hrn, 'node') not in existing_records:
                    try:
                        pkey = Keypair(create=True)
                        urn = hrn_to_urn(hrn, 'node')
                        node_gid = self.auth_hierarchy.create_gid(urn, create_uuid(), pkey)
                        node_record = RegNode ()
                        node_record.type='node'
                        node_record.hrn=hrn
                        node_record.gid=node_gid
                        node_record.pointer =node['node_id']
                        node_record.authority=get_authority(hrn)
                        dbsession.add(node_record)
                        dbsession.commit()
                        self.logger.info("Import: imported node: %s" % node_record)  
                    except:
                        self.logger.log_exc("Import: failed to import node") 
                    

            # import slices
            for slice_id in site['slice_ids']:
                if slice_id not in slices_dict:
                    continue 
                slice = slices_dict[slice_id]
                hrn = slicename_to_hrn(interface_hrn, slice['name'])
                if hrn not in existing_hrns or \
                   (hrn, 'slice') not in existing_records:
                    try:
                        pkey = Keypair(create=True)
                        urn = hrn_to_urn(hrn, 'slice')
                        slice_gid = self.auth_hierarchy.create_gid(urn, create_uuid(), pkey)
                        slice_record = RegSlice ()
                        slice_record.type='slice'
                        slice_record.hrn=hrn
                        slice_record.gid=slice_gid
                        slice_record.pointer=slice['slice_id']
                        slice_record.authority=get_authority(hrn)
                        dbsession.add(slice_record)
                        dbsession.commit()
                        self.logger.info("Import: imported slice: %s" % slice_record)  
                    except:
                        self.logger.log_exc("Import: failed to  import slice")

            # import persons
            for person_id in site['person_ids']:
                if person_id not in persons_dict:
                    continue 
                person = persons_dict[person_id]
                hrn = email_to_hrn(site_hrn, person['email'])
                if len(hrn) > 64:
                    hrn = hrn[:64]
    
                # if user's primary key has changed then we need to update the 
                # users gid by forcing an update here
                old_keys = []
                new_keys = []
                if person_id in old_person_keys:
                    old_keys = old_person_keys[person_id]
                if person_id in person_keys:
                    new_keys = person_keys[person_id]
                update_record = False
                for key in new_keys:
                    if key not in old_keys:
                        update_record = True 
    
                if hrn not in existing_hrns or \
                   (hrn, 'user') not in existing_records or update_record:
                    try:
                        if 'key_ids' in person and person['key_ids']:
                            key = new_keys[0]
                            try:
                                pkey = convert_public_key(key)
                            except:
                                self.logger.warn('unable to convert public key for %s' % hrn)
                                pkey = Keypair(create=True)
                        else:
                            # the user has no keys. Creating a random keypair for the user's gid
                            self.logger.warn("Import: person %s does not have a PL public key"%hrn)
                            pkey = Keypair(create=True) 
                        urn = hrn_to_urn(hrn, 'user')
                        person_gid = self.auth_hierarchy.create_gid(urn, create_uuid(), pkey)
                        person_record = RegUser ()
                        person_record.type='user'
                        person_record.hrn=hrn
                        person_record.gid=person_gid
                        person_record.pointer=person['person_id']
                        person_record.authority=get_authority(hrn)
                        dbsession.add (person_record)
                        dbsession.commit()
                        self.logger.info("Import: imported person: %s" % person_record)
                    except:
                        self.logger.log_exc("Import: failed to import person.") 
    
        # remove stale records    
        system_records = [interface_hrn, root_auth, interface_hrn + '.slicemanager']
        for (record_hrn, type) in existing_records.keys():
            if record_hrn in system_records:
                continue
            
            record = existing_records[(record_hrn, type)]
            if record.peer_authority:
                continue
    
            # dont delete vini's internet2 placeholdder record
            # normally this would be deleted becuase it does not have a plc record 
            if ".vini" in interface_hrn and interface_hrn.endswith('vini') and \
               record_hrn.endswith("internet2"):     
                continue
    
            found = False
            
            if type == 'authority':    
                for site in sites:
                    site_hrn = interface_hrn + "." + site['login_base']
                    if site_hrn == record_hrn and site['site_id'] == record.pointer:
                        found = True
                        break

            elif type == 'user':
                login_base = get_leaf(get_authority(record_hrn))
                username = get_leaf(record_hrn)
                if login_base in sites_dict:
                    site = sites_dict[login_base]
                    for person in persons:
                        tmp_username = person['email'].split("@")[0]
                        alt_username = person['email'].split("@")[0].replace(".", "_").replace("+", "_")
                        if username in [tmp_username, alt_username] and \
                           site['site_id'] in person['site_ids'] and \
                           person['person_id'] == record.pointer:
                            found = True
                            break
        
            elif type == 'slice':
                slicename = hrn_to_pl_slicename(record_hrn)
                for slice in slices:
                    if slicename == slice['name'] and \
                       slice['slice_id'] == record.pointer:
                        found = True
                        break    
 
            elif type == 'node':
                login_base = get_leaf(get_authority(record_hrn))
                nodename = Xrn.unescape(get_leaf(record_hrn))
                if login_base in sites_dict:
                    site = sites_dict[login_base]
                    for node in nodes:
                        tmp_nodename = node['hostname']
                        if tmp_nodename == nodename and \
                           node['site_id'] == site['site_id'] and \
                           node['node_id'] == record.pointer:
                            found = True
                            break  
            else:
                continue 
        
            if not found:
                try:
                    record_object = existing_records[(record_hrn, type)]
                    self.logger.info("Import: deleting record: %s" % record)
                    dbsession.delete(record_object)
                    dbsession.commit()
                except:
                    self.logger.log_exc("Import: failded to delete record")                    

        # save pub keys
        self.logger.info('Import: saving current pub keys')
        save_keys(keys_filename, person_keys)                
        