# our own simplistic replacement for six
try:
    StringType = basestring
except:
    StringType = str

try:
    from StringIO import StringIO
except:
    from io import StringIO

try:
    import xmlrpclib as xmlrpc_client
except:
    from xmlrpc import client as xmlrpc_client

try:
    import httplib as http_client
except:
    from http import client as http_client
    
try:
    import ConfigParser
except:
    import configparser as ConfigParser
