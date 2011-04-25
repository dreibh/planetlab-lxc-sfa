#!/usr/bin/python 
from lxml import etree
from StringIO import StringIO
from sfa.rspecs.rspec import RSpec 
from sfa.util.xrn import *
from sfa.util.plxrn import hostname_to_urn
from sfa.util.config import Config  

class PGRSpec(RSpec):
    xml = None
    header = '<?xml version="1.0"?>\n'
    namespaces = {'rspecv2':'http://www.protogeni.net/resources/rspec/0.2',
                  'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
                 }
    schemas =  {'xsi': 'http://www.protogeni.net/resources/rspec/0.2 http://www.protogeni.net/resources/rspec/0.2/ad.xsd'
            }
    type = 'pg'

    def create(self, type="advertisement"):
        RSpec.create(self)
        for namespace in self.namespaces:
            xmlns = "xmlns"
            if namespace not in 'rspecv2':
                xmlns = xmlns + ":" + namespace
            self.xml.set(xmlns, self.namespaces[namespace])
        for schema in self.schemas:
            self.xml.set(schema+":schemaLocation", self.schemas[schema])

    def get_network(self):
        network = None 
        nodes = self.xml.xpath('//rspecv2:node[@component_manager_uuid][1]', self.namespaces)
        if nodes:
            network  = nodes[0].get('component_manager_uuid')
        return network

    def get_networks(self):
        networks = self.xml.xpath('//rspecv2:node[@component_manager_uuid]/@component_manager_uuid')
        return set(networks)

    def get_node_elements(self):
        nodes = self.xml.xpath('//rspecv2:node', self.namespaces)
        return nodes

    def get_nodes(self, network=None):
        return self.xml.xpath('//rspecv2:node[@component_uuid]/@component_uuid', self.namespaces) 

    def get_nodes_with_slivers(self, network=None):
        if network:
            return self.xml.xpath('//node[@component_manager_uuid="%s"][sliver_type]/@component_uuid' % network, self.namespaces)
        else:
            return self.xml.xpath('//node[sliver_type]/@component_uuid' % network, self.namespaces)

    def get_nodes_without_slivers(self, network=None):
        pass

    def add_nodes(self, nodes, check_for_dupes=False):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for node in nodes:
            urn = ""
            if check_for_dupes and \
              self.xml.xpath('//rspecv2:node[@component_uuid="%s"]' % urn, self.namespaces):
                # node already exists
                continue
                
            node_tag = etree.SubElement(self.xml, 'node')
            node_type_tag = etree.SubElement(node_tag, 'node_type', type_name='pcvm', type_slots='100')
            available_tag = etree.SubElement(node_tag, 'available').text = 'true'
            exclusive_tag = etree.SubElement(node_tag, 'exclusive').text = 'false'
            location_tag = etree.SubElement(node_tag, 'location')
            interface_tag = etree.SubElement(node_tag, 'interface')
            

    def add_slivers(self, slivers, check_for_dupes=False): 
        pass

    def add_links(self, links, check_for_dupes=False):
        pass


if __name__ == '__main__':
    rspec = PGRSpec()
    rspec.add_nodes([1])
    print rspec