try:
    StringType = basestring
except:
    StringType = str

try:
    from StringIO import StringIO
except:
    from io import StringIO
