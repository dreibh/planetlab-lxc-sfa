# our own simplistic replacement for six
import sys
PY3 = sys.version_info[0] == 3

StringType = str
from io import StringIO

import xmlrpc.client as xmlrpc_client
import http.client as http_client
import configparser as ConfigParser
