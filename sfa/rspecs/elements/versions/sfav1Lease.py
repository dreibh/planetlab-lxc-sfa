from sfa.util.sfalogging import logger
from sfa.util.xml import XpathFilter
from sfa.util.xrn import Xrn
from sfa.util.sfatime import utcparse, datetime_to_string, datetime_to_epoch

from sfa.rspecs.elements.element import Element
from sfa.rspecs.elements.node import NodeElement
from sfa.rspecs.elements.sliver import Sliver
from sfa.rspecs.elements.location import Location
from sfa.rspecs.elements.hardware_type import HardwareType
from sfa.rspecs.elements.disk_image import DiskImage
from sfa.rspecs.elements.interface import Interface
from sfa.rspecs.elements.bwlimit import BWlimit
from sfa.rspecs.elements.pltag import PLTag
from sfa.rspecs.elements.versions.sfav1Sliver import SFAv1Sliver
from sfa.rspecs.elements.versions.sfav1PLTag import SFAv1PLTag
from sfa.rspecs.elements.versions.pgv2Services import PGv2Services
from sfa.rspecs.elements.lease import Lease


class SFAv1Lease:

    @staticmethod
    def add_leases(xml, leases):

        network_elems = xml.xpath('//network')
        if len(network_elems) > 0:
            network_elem = network_elems[0]
        elif len(leases) > 0:
            network_urn = Xrn(leases[0]['component_id']
                              ).get_authority_urn().split(':')[0]
            network_elem = xml.add_element('network', name=network_urn)
        else:
            network_elem = xml

        # group the leases by slice and timeslots
        grouped_leases = []

        while leases:
            slice_id = leases[0]['slice_id']
            start_time = leases[0]['start_time']
            duration = leases[0]['duration']
            group = []

            for lease in leases:
                if slice_id == lease['slice_id'] and start_time == lease['start_time'] and duration == lease['duration']:
                    group.append(lease)

            grouped_leases.append(group)

            for lease1 in group:
                leases.remove(lease1)

        lease_elems = []
        for lease in grouped_leases:
            #lease[0]['start_time'] = datetime_to_string(utcparse(lease[0]['start_time']))

            lease_fields = ['slice_id', 'start_time', 'duration']
            lease_elem = network_elem.add_instance(
                'lease', lease[0], lease_fields)
            lease_elems.append(lease_elem)

            # add nodes of this lease
            for node in lease:
                lease_elem.add_instance('node', node, ['component_id'])


#        lease_elems = []
#        for lease in leases:
#            lease_fields = ['lease_id', 'component_id', 'slice_id', 'start_time', 'duration']
#            lease_elem = network_elem.add_instance('lease', lease, lease_fields)
#            lease_elems.append(lease_elem)

    @staticmethod
    def get_leases(xml, filter=None):
        if filter is None:
            filter = {}
        xpath = '//lease%s | //default:lease%s' % (
            XpathFilter.xpath(filter), XpathFilter.xpath(filter))
        lease_elems = xml.xpath(xpath)
        return SFAv1Lease.get_lease_objs(lease_elems)

    @staticmethod
    def get_lease_objs(lease_elems):
        leases = []
        for lease_elem in lease_elems:
            # get nodes
            node_elems = lease_elem.xpath('./default:node | ./node')
            for node_elem in node_elems:
                lease = Lease(lease_elem.attrib, lease_elem)
                lease['slice_id'] = lease_elem.attrib['slice_id']
                #lease['start_time'] = datetime_to_epoch(utcparse(lease_elem.attrib['start_time']))
                lease['start_time'] = lease_elem.attrib['start_time']
                lease['duration'] = lease_elem.attrib['duration']
                lease['component_id'] = node_elem.attrib['component_id']
                leases.append(lease)

        return leases


#        leases = []
#        for lease_elem in lease_elems:
#            lease = Lease(lease_elem.attrib, lease_elem)
#            if lease.get('lease_id'):
#               lease['lease_id'] = lease_elem.attrib['lease_id']
#            lease['component_id'] = lease_elem.attrib['component_id']
#            lease['slice_id'] = lease_elem.attrib['slice_id']
#            lease['start_time'] = lease_elem.attrib['start_time']
#            lease['duration'] = lease_elem.attrib['duration']

#            leases.append(lease)
#        return leases
