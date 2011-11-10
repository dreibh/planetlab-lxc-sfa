
from sfa.util.xml import XpathFilter
from sfa.util.plxrn import PlXrn
from sfa.util.xrn import Xrn
from sfa.rspecs.elements.element import Element
from sfa.rspecs.elements.node import Node
from sfa.rspecs.elements.sliver import Sliver
from sfa.rspecs.elements.network import Network 
from sfa.rspecs.elements.location import Location
from sfa.rspecs.elements.hardware_type import HardwareType
from sfa.rspecs.elements.disk_image import DiskImage
from sfa.rspecs.elements.interface import Interface
from sfa.rspecs.elements.bwlimit import BWlimit
from sfa.rspecs.elements.pltag import PLTag
from sfa.rspecs.rspec_elements import RSpecElement, RSpecElements
from sfa.rspecs.elements.versions.sfav1Network import SFAv1Network
from sfa.rspecs.elements.versions.sfav1Sliver import SFAv1Sliver
from sfa.rspecs.elements.versions.sfav1PLTag import SFAv1PLTag
from sfa.rspecs.elements.versions.pgv2Services import PGv2Services

class SFAv1Node:

    @staticmethod
    def add_nodes(xml, nodes):
        network_elems = SFAv1Network.get_networks(xml)
        if len(network_elems) > 0:
            network_elem = network_elems[0]
        elif len(nodes) > 0 and nodes[0].get('component_manager_id'):
            network_elem = SFAv1Network.add_network(xml.root, {'name': nodes[0]['component_manager_id']})

        node_elems = []       
        for node in nodes:
            node_fields = ['component_manager_id', 'component_id', 'boot_state']
            elems = Element.add(network_elem, 'node', node, node_fields)
            node_elem = elems[0]  
            node_elems.append(node_elem)

            # determine network hrn
            network_hrn = None 
            if 'component_manager_id' in node and node['component_manager_id']:
                network_hrn = Xrn(node['component_manager_id']).get_hrn()

            # set component_name attribute and  hostname element
            if 'component_id' in node and node['component_id']:
                xrn = Xrn(node['component_id'])
                node_elem.set('component_name', xrn.get_leaf())
                hostname_tag = node_elem.add_element('hostname')
                hostname_tag.set_text(xrn.get_leaf())

            # set site id
            if 'authority_id' in node and node['authority_id']:
                node_elem.set('site_id', node['authority_id'])

            location_elems = Element.add(node_elem, 'location', node.get('location', []), Location.fields)
            interface_elems = Element.add(node_elem, 'interface', node.get('interfaces', []), Interface.fields)
            # need to generate the device id in the component_id
            i=0
            for interface_elem in interface_elems:
                comp_id = PlXrn(auth=network, interface='node%s:eth%s' % (interface['node_id'], i)).get_urn()
                interface_elem.set('component_id', comp_id)      
                i++ 
            
            #if 'bw_unallocated' in node and node['bw_unallocated']:
            #    bw_unallocated = etree.SubElement(node_elem, 'bw_unallocated', units='kbps').text = str(int(node['bw_unallocated'])/1000)

            PGv2Services.add_services(node_elem, node.get('services', []))
            SFAv1PLTags.add_tags(node_elem, node.get('tags', [])) 
            SFAv1Sliver.add_slivers(node_elem, node.get('slivers', []))

    @staticmethod 
    def add_slivers(xml, slivers):
        component_ids = []
        for sliver in slivers:
            filter = {}
            if isinstance(sliver, str):
                filter['component_id'] = '*%s*' % sliver
                sliver = {}
            elif 'component_id' in sliver and sliver['component_id']:
                filter['component_id'] = '*%s*' % sliver['component_id']
            nodes = SFAv1Node.get_nodes(xml, filter)
            if not nodes:
                continue
            node = nodes[0]
            SFAv1Sliver.add_slivers(node, sliver)

    @staticmethod
    def remove_slivers(xml, hostnames):
        for hostname in hostnames:
            nodes = SFAv1Node.get_nodes(xml, {'component_id': '*%s*' % hostname})
            for node in nodes:
                slivers = SFAv1Slivers.get_slivers(node.element)
                for sliver in slivers:
                    node.element.remove(sliver.element)
        
    @staticmethod
    def get_nodes(xml, filter={}):
        xpath = '//node%s | //default:node%s' % (XpathFilter.xpath(filter), XpathFilter.xpath(filter))
        node_elems = xml.xpath(xpath)
        return SFAv1Node.get_node_objs(node_elems)

    @staticmethod
    def get_nodes_with_slivers(xml):
        xpath = '//node/sliver | //default:node/default:sliver' % (XpathFilter.xpath(filter), XpathFilter.xpath(filter))
        node_elems = xml.xpath(xpath)
        return SFAv1Node.get_nodes_objs(node_elems)


    @staticmethod
    def get_node_objs(node_elems):
        nodes = []    
        for node_elem in node_elems:
            node = Node(node_elem.attrib, node_elem)
            if 'site_id' in node_elem.attrib:
                node['authority_id'] = node_elem.attrib['site_id']
            location_objs = Element.get(node_elem, './default:location | ./location', Location)
            if len(location_objs) > 0:
                node['location'] = location_objs[0]
            bwlimit_objs = Element.get(node_elem, './default:bw_limit | ./bw_limit', BWlimit)
            if len(bwlimit_objs) > 0:
                node['bwlimit'] = bwlimit_objs[0]
            node['interfaces'] = Element.get(node_elem, './default:interface | ./interface', Interface)
            node['services'] = PGv2Services.get_services(node_elem) 
            node['slivers'] = SFAv1Sliver.get_slivers(node_elem)
            node['tags'] =  SFAv1PLTag.get_pl_tags(node_elem, ignore=Node.fields.keys())
            nodes.append(node)
        return nodes            
            