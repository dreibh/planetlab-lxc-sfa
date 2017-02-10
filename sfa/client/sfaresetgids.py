#!/usr/bin/python

from __future__ import print_function

from argparse import ArgumentParser

from sfa.util.config import Config
from sfa.storage.alchemy import alchemy
from sfa.storage.model import RegRecord
from sfa.trust.hierarchy import Hierarchy
from sfa.trust.certificate import convert_public_key, Keypair

"""
WARNING : This script is not exactly thoroughly tested

BEFORE YOU USE
* backup the sfa db
* backup the /var/lib/sfa/authorities tree
* make sure to keep all this for a while 
  in case for example the old uuids turn out to be needed

PURPOSE

Regenerates gids; mostly useful when your root gid is old or obsolete
for any other reason (like, it's still md5 signed)

POLICIES

all  : regenerate everything no matter what, including toplevel gid
safe : regenerate everything *except* toplevel 
incremental : was useful during development mostly; 

WHAT IT DOES

authorities : a new gid is issued
users : a new gid is created with email, pubkey, and uuid restored from the previous ones

HOW TO USE

. do the backups - see above
. shutdown your sfa service
. rm -rf /var/lib/sfa/authorities
. run the script (run directly with python, no entry point is installed in PATH)
. restart the service

. on the client side, trash any old sscert or gids or similar

"""


class SfaResetGids:
    def __init__(self, session, tophrn):
        self.session = session
        self.tophrn = tophrn

    def load_local_records(self):
        """
        read the database for records that start with tophrn.*
        and sort them by hrn
        """
        # just making sure we don't mess with anything else
        # than our own local business
        self.records = self.session.query(RegRecord)\
                       .filter(RegRecord.hrn.op('~')("{}.*".format(self.tophrn)))\
                       .order_by(RegRecord.hrn)

    def regenerate(self, policy='safe'):
        """
        For all local records, gid gets regenerated
        policy parameter works as follows
        * all :
          all gids get renewed, including toplevel hrn, no matter what
        * safe : 
          gid for toplevel hrn gets regenerated only if not yet existing
          in SFA_DATA_DIR (i.e. /var/lib/sfa/authorities/<hrn>/hrn.{gid,key})
          all others are redone
        * incremental :
          recreate only for entities not present in SFA_DATA_DIR
        """

        count_auths, count_users, count_slices = 0, 0, 0
        hierarchy = Hierarchy()
        for record in self.records:
            print(record.hrn)
            ########## not an autority nor a user nor a slice: ignored
            # Just wondering what other type it could be...
            if record.type not in ['authority', 'user', 'slice']:
                message = ''
                if record.gid:
                    message = '[GID cleared]'
                    record.gid = None
                print("SKP (non-auth) {} {} : {}"
                      .format(message, record.type, record.hrn))
                continue
            ########## toplevel : be careful 
            if record.hrn == self.tophrn:
                if policy != 'all':
                    print("SKP (toplevel) - type={} - policy={}"
                          .format(record.type, policy))
                    continue
            ########## user : rebuild a gid from pubkey and email
            if record.type == 'user':
                hrn = str(record.hrn)
                gid = record.get_gid_object()
                uuid = gid.get_uuid()
                pub = gid.get_pubkey()
                email = gid.get_email()
                print("pub {} uuid {}... email {}".format(pub, str(uuid)[:6], email))
                new_gid = hierarchy.create_gid(hrn, uuid, pub, email=email)
                new_gid_str = new_gid.save_to_string()
                record.gid = new_gid_str
                print("NEW {} {} [{}]".format(record.type, record.hrn, email))
                count_users += 1
                continue
            ########## authorities
            if record.type == 'authority':
                if policy in ('all', 'safe'):
                    redo = True
                else:
                    redo = not hierarchy.auth_exists(record.hrn)
                if not redo:
                    print("IGN (existing) {}".format(record.hrn))
                else:
                    print("NEW {} {}".format(record.type, record.hrn))
                    # because we have it sorted we should not need create_parents
                    gid = hierarchy.create_auth(str(record.hrn))
                    record.gid = gid
                    count_auths += 1
            ########## slices
            if record.type == 'slice':
                hrn = str(record.hrn)
                gid = record.get_gid_object()
                uuid = gid.get_uuid()
                pub = gid.get_pubkey()
                print("pub {} uuid {}...".format(pub, str(uuid)[:6]))
                new_gid = hierarchy.create_gid(hrn, uuid, pub)
                new_gid_str = new_gid.save_to_string()
                record.gid = new_gid_str
                print("NEW {} {}".format(record.type, record.hrn))
                count_slices += 1
                continue
        #
        print("Committing to the DB {} new auth gids and {} new user gids and {} new slice gids"
              .format(count_auths, count_users, count_slices))
        self.session.commit()
        return True

    def main(self):
        parser = ArgumentParser()
        parser.add_argument("--policy", choices=('all', 'safe', 'incremental'),
                            default='safe')
        args = parser.parse_args()

        self.load_local_records()
        return 0 if self.regenerate(args.policy) else 1

###
if __name__ == '__main__':
    session = alchemy.session()
    tophrn = Config().SFA_REGISTRY_ROOT_AUTH
    print(tophrn)
    SfaResetGids(session, tophrn).main()
