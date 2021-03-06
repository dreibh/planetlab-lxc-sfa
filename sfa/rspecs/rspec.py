#!/usr/bin/env python3



from datetime import datetime, timedelta

from sfa.util.xml import XML, XpathFilter
from sfa.util.faults import InvalidRSpecElement, InvalidRSpec
from sfa.util.sfatime import SFATIME_FORMAT

from sfa.rspecs.rspec_elements import RSpecElement, RSpecElements
from sfa.rspecs.version_manager import VersionManager


class RSpec:

    def __init__(self, rspec="", version=None, user_options=None, ttl=None, expires=None):
        if user_options is None:
            user_options = {}
        self.header = '<?xml version="1.0"?>\n'
        self.template = """<RSpec></RSpec>"""
        self.version = None
        self.xml = XML()
        self.version_manager = VersionManager()
        self.user_options = user_options
        self.ttl = ttl
        self.expires = expires
        self.elements = {}
        if rspec:
            if version:
                self.version = self.version_manager.get_version(version)
                self.parse_xml(rspec, version)
            else:
                self.parse_xml(rspec)
        elif version:
            self.create(version, ttl, expires)
        else:
            raise InvalidRSpec(
                "No RSpec or version specified. Must specify a valid rspec string or a valid version")

    def create(self, version=None, ttl=None, expires=None):
        """
        Create root element
        ttl: time to live in minutes, this will determine the expires tag of the RSpec
        """
        self.version = self.version_manager.get_version(version)
        self.namespaces = self.version.namespaces
        self.parse_xml(self.version.template, self.version)
        now = datetime.utcnow()
        generated_ts = now.strftime(SFATIME_FORMAT)
        if ttl is None:
            ttl = 60
        if expires is None:
            expires_ts = (now + timedelta(minutes=ttl)
                          ).strftime(SFATIME_FORMAT)
        else:
            if isinstance(expires, int):
                expires_date = datetime.fromtimestamp(expires)
            else:
                expires_date = expires
            expires_ts = expires_date.strftime(SFATIME_FORMAT)
        self.xml.set('expires', expires_ts)
        self.xml.set('generated', generated_ts)

    def parse_xml(self, xml, version=None):
        self.xml.parse_xml(xml)
        if not version:
            if self.xml.schema:
                self.version = self.version_manager.get_version_by_schema(
                    self.xml.schema)
            else:
                #raise InvalidRSpec('unknown rspec schema: {}'.format(schema))
                # TODO: Should start raising an exception once SFA defines a schema.
                # for now we just  default to sfa
                self.version = self.version_manager.get_version(
                    {'type': 'sfa', 'version': '1'})
        self.version.xml = self.xml
        self.namespaces = self.xml.namespaces

    def load_rspec_elements(self, rspec_elements):
        self.elements = {}
        for rspec_element in rspec_elements:
            if isinstance(rspec_element, RSpecElement):
                self.elements[rspec_element.type] = rspec_element

    def register_rspec_element(self, element_type, element_name, element_path):
        if element_type not in RSpecElements:
            raise InvalidRSpecElement(element_type,
                                      extra="no such element type: {}. Must specify a valid RSpecElement".format(element_type))
        self.elements[element_type] = RSpecElement(
            element_type, element_name, element_path)

    def get_rspec_element(self, element_type):
        if element_type not in self.elements:
            msg = "ElementType {} not registered for this rspec".format(
                element_type)
            raise InvalidRSpecElement(element_type, extra=msg)
        return self.elements[element_type]

    def get(self, element_type, filter=None, depth=0):
        if filter is None:
            filter = {}
        elements = self.get_elements(element_type, filter)
        elements = [self.xml.get_element_attributes(
            elem, depth=depth) for elem in elements]
        return elements

    def get_elements(self, element_type, filter=None):
        """
        search for a registered element
        """
        if filter is None:
            filter = {}
        if element_type not in self.elements:
            msg = "Unable to search for element {} in rspec, expath expression not found."\
                  .format(element_type)
            raise InvalidRSpecElement(element_type, extra=msg)
        rspec_element = self.get_rspec_element(element_type)
        xpath = rspec_element.path + XpathFilter.xpath(filter)
        return self.xml.xpath(xpath)

    def merge(self, in_rspec):
        self.version.merge(in_rspec)

    def filter(self, filter):
        if 'component_manager_id' in filter:
            nodes = self.version.get_nodes()
            for node in nodes:
                if 'component_manager_id' not in node.attrib or \
                        node.attrib['component_manager_id'] != filter['component_manager_id']:
                    parent = node.getparent()
                    parent.remove(node.element)

    def toxml(self, header=True):
        if header:
            return self.header + self.xml.toxml()
        else:
            return self.xml.toxml()

    def save(self, filename):
        return self.xml.save(filename)

if __name__ == '__main__':
    import sys
    input = sys.argv[1]
    with open(input) as f:
        rspec = RSpec(f.read())
    print(rspec)
#    rspec.register_rspec_element(RSpecElements.NETWORK, 'network', '//network')
#    rspec.register_rspec_element(RSpecElements.NODE, 'node', '//node')
#    print rspec.get(RSpecElements.NODE)[0]
#    print rspec.get(RSpecElements.NODE, depth=1)[0]
