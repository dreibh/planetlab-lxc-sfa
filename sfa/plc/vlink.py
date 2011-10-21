# Taken from bwlimit.py
#
# See tc_util.c and http://physics.nist.gov/cuu/Units/binary.html. Be
# warned that older versions of tc interpret "kbps", "mbps", "mbit",
# and "kbit" to mean (in this system) "kibps", "mibps", "mibit", and
# "kibit" and that if an older version is installed, all rates will
# be off by a small fraction.
suffixes = {
    "":         1,
    "bit":  1,
    "kibit":    1024,
    "kbit": 1000,
    "mibit":    1024*1024,
    "mbit": 1000000,
    "gibit":    1024*1024*1024,
    "gbit": 1000000000,
    "tibit":    1024*1024*1024*1024,
    "tbit": 1000000000000,
    "bps":  8,
    "kibps":    8*1024,
    "kbps": 8000,
    "mibps":    8*1024*1024,
    "mbps": 8000000,
    "gibps":    8*1024*1024*1024,
    "gbps": 8000000000,
    "tibps":    8*1024*1024*1024*1024,
    "tbps": 8000000000000
}

def get_tc_rate(s):
    """
    Parses an integer or a tc rate string (e.g., 1.5mbit) into bits/second
    """

    if type(s) == int:
        return s
    m = re.match(r"([0-9.]+)(\D*)", s)
    if m is None:
        return -1
    suffix = m.group(2).lower()
    if suffixes.has_key(suffix):
        return int(float(m.group(1)) * suffixes[suffix])
    else:
        return -1

def format_tc_rate(rate):
    """
    Formats a bits/second rate into a tc rate string
    """

    if rate >= 1000000000 and (rate % 1000000000) == 0:
        return "%.0fgbit" % (rate / 1000000000.)
    elif rate >= 1000000 and (rate % 1000000) == 0:
        return "%.0fmbit" % (rate / 1000000.)
    elif rate >= 1000:
        return "%.0fkbit" % (rate / 1000.)
    else:
        return "%.0fbit" % rate

def get_link_id(if1, if2):
    if if1['id'] < if2['id']:
        link = (if1['id']<<7) + if2['id']
    else:
        link = (if2['id']<<7) + if1['id']
    return link

def get_iface_id(if1, if2):
    if if1['id'] < if2['id']:
        iface = 1
    else:
        iface = 2
    return iface

def get_virt_ip(if1, if2):
    link_id = get_link_id(if1, if2)
    iface_id = get_iface_id(if1, if2)
    first = link_id >> 6
    second = ((link_id & 0x3f)<<2) + iface_id
    return "192.168.%d.%s" % (frist, second)

def get_virt_net(link):
    link_id = self.get_link_id(link)
    first = link_id >> 6
    second = (link_id & 0x3f)<<2
    return "192.168.%d.%d/30" % (first, second)

def get_interface_id(interface):
    if_name = PlXrn(interface=interface['component_id']).interface_name()
    node, dev = if_name.split(":")
    node_id = int(node.replace("pc", ""))
    return node_id

    
def get_topo_rspec(self, link):
    link['interface1']['id'] = get_interface_id(link['interface1'])
    link['interface2']['id'] = get_interface_id(link['interface2'])
    my_ip = get_virt_ip(link['interface1'], link['interface2'])
    remote_ip = get_virt_ip(link['interface2'], link['interface1'])
    net = get_virt_net(link)
    bw = format_tc_rate(long(link['capacity']))
    ipaddr = remote.get_primary_iface().ipv4
    return (link['interface2']['id'], ipaddr, bw, my_ip, remote_ip, net) 
