#----------------------------------------------------------------------
# Copyright (c) 2008 Board of Trustees, Princeton University
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
#----------------------------------------------------------------------
#
# implements SFA tickets
#



from sfa.trust.certificate import Certificate
from sfa.trust.gid import GID

import xmlrpc.client

# Ticket is tuple:
#   (gidCaller, gidObject, attributes, rspec, delegate)
#
#    gidCaller = GID of the caller performing the operation
#    gidObject = GID of the slice
#    attributes = slice attributes (keys, vref, instantiation, etc)
#    rspec = resources


class SfaTicket(Certificate):
    gidCaller = None
    gidObject = None
    attributes = {}
    rspec = {}
    delegate = False

    def __init__(self, create=False, subject=None, string=None, filename=None):
        Certificate.__init__(self, create, subject, string, filename)

    def set_gid_caller(self, gid):
        self.gidCaller = gid

    def get_gid_caller(self):
        if not self.gidCaller:
            self.decode()
        return self.gidCaller

    def set_gid_object(self, gid):
        self.gidObject = gid

    def get_gid_object(self):
        if not self.gidObject:
            self.decode()
        return self.gidObject

    def set_attributes(self, gid):
        self.attributes = gid

    def get_attributes(self):
        if not self.attributes:
            self.decode()
        return self.attributes

    def set_rspec(self, gid):
        self.rspec = gid

    def get_rspec(self):
        if not self.rspec:
            self.decode()
        return self.rspec

    def set_delegate(self, delegate):
        self.delegate = delegate

    def get_delegate(self):
        if not self.delegate:
            self.decode()
        return self.delegate

    def encode(self):
        dict = {"gidCaller": None,
                "gidObject": None,
                "attributes": self.attributes,
                "rspec": self.rspec,
                "delegate": self.delegate}
        if self.gidCaller:
            dict["gidCaller"] = self.gidCaller.save_to_string(
                save_parents=True)
        if self.gidObject:
            dict["gidObject"] = self.gidObject.save_to_string(
                save_parents=True)
        str = "URI:" + xmlrpc.client.dumps((dict,), allow_none=True)
        self.set_data(str)

    def decode(self):
        data = self.get_data()
        if data:
            dict = xmlrpc.client.loads(self.get_data()[4:])[0][0]
        else:
            dict = {}

        self.attributes = dict.get("attributes", {})
        self.rspec = dict.get("rspec", {})
        self.delegate = dict.get("delegate", False)

        gidCallerStr = dict.get("gidCaller", None)
        if gidCallerStr:
            self.gidCaller = GID(string=gidCallerStr)
        else:
            self.gidCaller = None

        gidObjectStr = dict.get("gidObject", None)
        if gidObjectStr:
            self.gidObject = GID(string=gidObjectStr)
        else:
            self.gidObject = None

    def dump(self, dump_parents=False):
        print("TICKET", self.get_subject())

        print("  gidCaller:")
        gidCaller = self.get_gid_caller()
        if gidCaller:
            gidCaller.dump(8, dump_parents)

        print("  gidObject:")
        gidObject = self.get_gid_object()
        if gidObject:
            gidObject.dump(8, dump_parents)

        print("  attributes:")
        for attrname in list(self.get_attributes().keys()):
            print("        ", attrname, self.get_attributes()[attrname])

        print("       rspec:")
        print("        ", self.get_rspec())

        if self.parent and dump_parents:
            print("PARENT", end=' ')
            self.parent.dump(dump_parents)
