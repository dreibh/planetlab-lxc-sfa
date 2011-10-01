from lxml import etree
from copy import deepcopy
from StringIO import StringIO
from sfa.util.xrn import *
from sfa.util.plxrn import hostname_to_urn, xrn_to_hostname 
from sfa.rspecs.rspec_version import BaseVersion
from sfa.rspecs.rspec_elements import RSpecElement, RSpecElements

class PGv2(BaseVersion):
    type = 'ProtoGENI'
    content_type = 'ad'
    version = '2'
    schema = 'http://www.protogeni.net/resources/rspec/2/ad.xsd'
    namespace = 'http://www.protogeni.net/resources/rspec/2'
    extensions = {
        'flack': "http://www.protogeni.net/resources/rspec/ext/flack/1",
        'planetlab': "http://www.planet-lab.org/resources/sfa/ext/planetlab/1",
    }
    namespaces = dict(extensions.items() + [('default', namespace)])
    elements = [
        RSpecElement(RSpecElements.NETWORK, 'network', '//default:node[@component_manager_id][1]'),
        RSpecElement(RSpecElements.NODE, 'node', '//default:node | //node'),
        RSpecElement(RSpecElements.SLIVER, 'sliver', '//default:node/default:sliver_type | //node/sliver_type'),
    ]

    def get_network(self):
        network = None
        nodes = self.xml.xpath('//default:node[@component_manager_id][1]', namespaces=self.namespaces)
        if nodes:
            network  = nodes[0].get('component_manager_id')
        return network

    def get_networks(self):
        networks = self.xml.xpath('//default:node[@component_manager_id]/@component_manager_id', namespaces=self.namespaces)
        return set(networks)

    def get_node_element(self, hostname, network=None):
        nodes = self.xml.xpath('//default:node[@component_id[contains(., "%s")]] | node[@component_id[contains(., "%s")]]' % (hostname, hostname), namespaces=self.namespaces)
        if isinstance(nodes,list) and nodes:
            return nodes[0]
        else:
            return None

    def get_node_elements(self, network=None):
        nodes = self.xml.xpath('//default:node | //node', namespaces=self.namespaces)
        return nodes


    def get_nodes(self, network=None):
        xpath = '//default:node[@component_name]/@component_id | //node[@component_name]/@component_id'
        nodes = self.xml.xpath(xpath, namespaces=self.namespaces)
        nodes = [xrn_to_hostname(node) for node in nodes]
        return nodes

    def get_nodes_with_slivers(self, network=None):
        if network:
            nodes = self.xml.xpath('//default:node[@component_manager_id="%s"][sliver_type]/@component_id' % network, namespaces=self.namespaces)
        else:
            nodes = self.xml.xpath('//default:node[default:sliver_type]/@component_id', namespaces=self.namespaces)
        nodes = [xrn_to_hostname(node) for node in nodes]
        return nodes

    def get_nodes_without_slivers(self, network=None):
        return []

    def get_sliver_attributes(self, hostname, network=None):
        node = self.get_node_element(hostname, network)
        sliver = node.xpath('./default:sliver_type', namespaces=self.namespaces)
        if sliver is not None and isinstance(sliver, list):
            sliver = sliver[0]
        return self.attributes_list(sliver)

    def get_slice_attributes(self, network=None):
        slice_attributes = []
        nodes_with_slivers = self.get_nodes_with_slivers(network)
        # TODO: default sliver attributes in the PG rspec?
        default_ns_prefix = self.namespaces['default']
        for node in nodes_with_slivers:
            sliver_attributes = self.get_sliver_attributes(node, network)
            for sliver_attribute in sliver_attributes:
                name=str(sliver_attribute[0])
                text =str(sliver_attribute[1])
                attribs = sliver_attribute[2]
                # we currently only suppor the <initscript> and <flack> attributes
                if  'info' in name:
                    attribute = {'name': 'flack_info', 'value': str(attribs), 'node_id': node}
                    slice_attributes.append(attribute)
                elif 'initscript' in name:
                    if attribs is not None and 'name' in attribs:
                        value = attribs['name']
                    else:
                        value = text
                    attribute = {'name': 'initscript', 'value': value, 'node_id': node}
                    slice_attributes.append(attribute)

        return slice_attributes

    def attributes_list(self, elem):
        opts = []
        if elem is not None:
            for e in elem:
                opts.append((e.tag, str(e.text).strip(), e.attrib))
        return opts

    def get_default_sliver_attributes(self, network=None):
        return []

    def add_default_sliver_attribute(self, name, value, network=None):
        pass

    def add_nodes(self, nodes, check_for_dupes=False):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for node in nodes:
            urn = ""
            if check_for_dupes and \
              self.xml.xpath('//default:node[@component_uuid="%s"]' % urn, namespaces=self.namespaces):
                # node already exists
                continue

            node_tag = etree.SubElement(self.xml, 'node', exclusive='false')
            if 'network_urn' in node:
                node_tag.set('component_manager_id', node['network_urn'])
            if 'urn' in node:
                node_tag.set('component_id', node['urn'])
            if 'hostname' in node:
                node_tag.set('component_name', node['hostname'])
            # TODO: should replace plab-pc with pc model
            node_type_tag = etree.SubElement(node_tag, 'hardware_type', name='plab-pc')
            node_type_tag = etree.SubElement(node_tag, 'hardware_type', name='pc')
            available_tag = etree.SubElement(node_tag, 'available', now='true')
            sliver_type_tag = etree.SubElement(node_tag, 'sliver_type', name='plab-vnode')

            pl_initscripts = node.get('pl_initscripts', {})
            for pl_initscript in pl_initscripts.values():
                etree.SubElement(sliver_type_tag, '{%s}initscript' % self.namespaces['planetlab'], name=pl_initscript['name'])

            # protogeni uses the <sliver_type> tag to identify the types of
            # vms available at the node.
            # only add location tag if longitude and latitude are not null
            if 'site' in node:
                longitude = node['site'].get('longitude', None)
                latitude = node['site'].get('latitude', None)
                if longitude and latitude:
                    location_tag = etree.SubElement(node_tag, 'location', country="us", \
                                                    longitude=str(longitude), latitude=str(latitude))

    def merge_node(self, source_node_tag):
        # this is untested
        self.xml.append(deepcopy(source_node_tag))

    def add_slivers(self, slivers, sliver_urn=None, no_dupes=False):

        # all nodes hould already be present in the rspec. Remove all
        # nodes that done have slivers
        slivers_dict = {}
        for sliver in slivers:
            if isinstance(sliver, basestring):
                slivers_dict[sliver] = {'hostname': sliver}
            elif isinstance(sliver, dict):
                slivers_dict[sliver['hostname']] = sliver        

        nodes = self.get_node_elements()
        for node in nodes:
            urn = node.get('component_id')
            hostname = xrn_to_hostname(urn)
            if hostname not in slivers_dict:
                parent = node.getparent()
                parent.remove(node)
            else:
                sliver_info = slivers_dict[hostname]
                node.set('client_id', hostname)
                if sliver_urn:
                    slice_id = sliver_info.get('slice_id', -1)
                    node_id = sliver_info.get('node_id', -1)
                    sliver_id = urn_to_sliver_id(sliver_urn, slice_id, node_id)
                    node.set('sliver_id', sliver_id)

                # remove existing sliver_type tags,it needs to be recreated
                sliver_elem = node.xpath('./default:sliver_type | ./sliver_type', namespaces=self.namespaces)
                if sliver_elem and isinstance(sliver_elem, list):
                    sliver_elem = sliver_elem[0]
                    node.remove(sliver_elem)

                sliver_elem = etree.SubElement(node, 'sliver_type', name='plab-vnode')
                for tag in sliver_info['tags']:
                    if tag['tagname'] == 'flack_info':
                        e = etree.SubElement(sliver_elem, '{%s}info' % self.namespaces['flack'], attrib=eval(tag['value']))
                    elif tag['tagname'] == 'initscript':
                        e = etree.SubElement(sliver_elem, '{%s}initscript' % self.namespaces['planetlab'], attrib={'name': tag['value']})



    def add_default_sliver_attribute(self, name, value, network=None):
        pass

    def add_interfaces(self, interfaces, no_dupes=False):
        pass

    def add_links(self, links, no_dupes=False):
        pass

    def merge(self, in_rspec):
        """
        Merge contents for specified rspec with current rspec
        """

        # just copy over all the child elements under the root element
        tree = etree.parse(StringIO(in_rspec))
        root = tree.getroot()
        for child in root.getchildren():
            self.xml.append(child)

    def cleanup(self):
        # remove unncecessary elements, attributes
        if self.type in ['request', 'manifest']:
            # remove 'available' element from remaining node elements
            self.remove_element('//default:available | //available')

class PGv2Ad(PGv2):
    enabled = True
    content_type = 'ad'
    schema = 'http://www.protogeni.net/resources/rspec/2/ad.xsd'
    template = '<rspec xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.protogeni.net/resources/rspec/2" xsi:schemaLocation="http://www.protogeni.net/resources/rspec/2 http://www.protogeni.net/resources/rspec/2/ad.xsd" xmlns:flack="http://www.protogeni.net/resources/rspec/ext/flack/1" xmlns:planetlab="http://www.planet-lab.org/resources/sfa/ext/planetlab/1" />'

class PGv2Request(PGv2):
    enabled = True
    content_type = 'request'
    schema = 'http://www.protogeni.net/resources/rspec/2/request.xsd'
    template = '<rspec xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.protogeni.net/resources/rspec/2" xsi:schemaLocation="http://www.protogeni.net/resources/rspec/2 http://www.protogeni.net/resources/rspec/2/request.xsd" xmlns:flack="http://www.protogeni.net/resources/rspec/ext/flack/1" xmlns:planetlab="http://www.planet-lab.org/resources/sfa/ext/planetlab/1" />'

class PGv2Manifest(PGv2):
    enabled = True
    content_type = 'manifest'
    schema = 'http://www.protogeni.net/resources/rspec/2/manifest.xsd'
    template = '<rspec xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.protogeni.net/resources/rspec/2" xsi:schemaLocation="http://www.protogeni.net/resources/rspec/2 http://www.protogeni.net/resources/rspec/2/manifest.xsd" xmlns:flack="http://www.protogeni.net/resources/rspec/ext/flack/1" xmlns:planetlab="http://www.planet-lab.org/resources/sfa/ext/planetlab/1" />'
     


if __name__ == '__main__':
    from sfa.rspecs.rspec import RSpec
    from sfa.rspecs.rspec_elements import *
    r = RSpec('/tmp/pg.rspec')
    r.load_rspec_elements(PGv2.elements)
    r.namespaces = PGv2.namespaces
    print r.get(RSpecElements.NODE)
