from sfa.util.sfalogging import logger
from sfa.util.xml import XpathFilter
from sfa.util.xrn import Xrn

from sfa.rspecs.elements.element import Element
from sfa.rspecs.elements.node import Node
from sfa.rspecs.elements.sliver import Sliver
from sfa.rspecs.elements.location import Location
from sfa.rspecs.elements.hardware_type import HardwareType
from sfa.rspecs.elements.disk_image import DiskImage
from sfa.rspecs.elements.interface import Interface
from sfa.rspecs.elements.bwlimit import BWlimit
from sfa.rspecs.elements.pltag import PLTag
from sfa.rspecs.elements.versions.nitosv1Sliver import NITOSv1Sliver
from sfa.rspecs.elements.versions.nitosv1PLTag import NITOSv1PLTag
from sfa.rspecs.elements.versions.pgv2Services import PGv2Services
from sfa.rspecs.elements.lease import Lease
from sfa.rspecs.elements.spectrum import Spectrum
from sfa.rspecs.elements.channel import Channel

from sfa.planetlab.plxrn import xrn_to_hostname

class NITOSv1Channel:

    @staticmethod
    def add_channels(xml, channels):
        
        network_elems = xml.xpath('//network')
        if len(network_elems) > 0:
            network_elem = network_elems[0]
        elif len(channels) > 0:
            #network_urn = Xrn(leases[0]['component_id']).get_authority_urn().split(':')[0]
            network_urn = "pla"
            network_elem = xml.add_element('network', name = network_urn)
        else:
            network_elem = xml

#        spectrum_elems = xml.xpath('//spectrum') 
#        spectrum_elem = xml.add_element('spectrum')

#        if len(spectrum_elems) > 0:
#            spectrum_elem = spectrum_elems[0]
#        elif len(channels) > 0:
#            spectrum_elem = xml.add_element('spectrum')
#        else:
#            spectrum_elem = xml

        spectrum_elem = network_elem.add_instance('spectrum', [])    
          
        channel_elems = []       
        for channel in channels:
            channel_fields = ['channel_num', 'frequency', 'standard']
            channel_elem = spectrum_elem.add_instance('channel', channel, channel_fields)
            channel_elems.append(channel_elem)


    @staticmethod
    def get_channels(xml, filter={}):
        xpath = '//channel%s | //default:channel%s' % (XpathFilter.xpath(filter), XpathFilter.xpath(filter))
        channel_elems = xml.xpath(xpath)
        return NITOSv1Channel.get_channel_objs(channel_elems)

    @staticmethod
    def get_channel_objs(channel_elems):
        channels = []    
        for channel_elem in channel_elems:
            channel = Channel(channel_elem.attrib, channel_elem)
            channel['channel_num'] = channel_elem.attrib['channel_num']
            channel['frequency'] = channel_elem.attrib['frequency']
            channel['standard'] = channel_elem.attrib['standard']

            channels.append(channel)
        return channels            

