

import os
from sfa.util.faults import InvalidRSpec, UnsupportedRSpecVersion
from sfa.rspecs.version import RSpecVersion
from sfa.util.sfalogging import logger


class VersionManager:

    def __init__(self):
        self.versions = []
        self.load_versions()

    def __repr__(self):
        return "<VersionManager with {} flavours: [{}]>"\
            .format(len(self.versions),
                    ", ".join([str(x) for x in self.versions]))

    def load_versions(self):
        path = os.path.dirname(os.path.abspath(__file__))
        versions_path = path + os.sep + 'versions'
        versions_module_path = 'sfa.rspecs.versions'
        valid_module = lambda x: os.path.isfile(os.sep.join([versions_path, x])) \
            and x.endswith('.py') and x != '__init__.py'
        files = [f for f in os.listdir(versions_path) if valid_module(f)]
        for filename in files:
            basename = filename.split('.')[0]
            module_path = versions_module_path + '.' + basename
            module = __import__(module_path, fromlist=module_path)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, 'version') and hasattr(attr, 'enabled') and attr.enabled == True:
                    self.versions.append(attr())

    def _get_version(self, type, version_num=None, content_type=None):
        retval = None
        for version in self.versions:
            if type is None or type.lower() == version.type.lower():
                if version_num is None or str(float(version_num)) == str(float(version.version)):
                    if content_type is None or content_type.lower() == version.content_type.lower() \
                            or version.content_type == '*':
                        retval = version
                        # sounds like we should be glad with the first match,
                        # not the last one
                        break
        if not retval:
            raise UnsupportedRSpecVersion(
                "[%s %s %s] is not suported here" % (type, version_num, content_type))
        return retval

    def get_version(self, version=None):
        retval = None
        if isinstance(version, dict):
            retval = self._get_version(version.get('type'), version.get(
                'version'), version.get('content_type'))
        elif isinstance(version, str):
            version_parts = version.split(' ')
            num_parts = len(version_parts)
            type = version_parts[0]
            version_num = None
            content_type = None
            if num_parts > 1:
                version_num = version_parts[1]
            if num_parts > 2:
                content_type = version_parts[2]
            retval = self._get_version(type, version_num, content_type)
        elif isinstance(version, RSpecVersion):
            retval = version
        elif not version:
            retval = self.versions[0]
        else:
            raise UnsupportedRSpecVersion(
                "No such version: %s " % str(version))

        return retval

    def get_version_by_schema(self, schema):
        retval = None
        for version in self.versions:
            if schema == version.schema:
                retval = version
        if not retval:
            raise InvalidRSpec("Unkwnown RSpec schema: %s" % schema)
        return retval

    def show_by_string(self, string):
        try:
            print(self.get_version(string))
        except Exception as e:
            print(e)

    def show_by_schema(self, string):
        try:
            print(self.get_version_by_schema(string))
        except Exception as e:
            print(e)

if __name__ == '__main__':
    manager = VersionManager()
    print(manager)
    manager.show_by_string('sfa 1')
    manager.show_by_string('protogeni 2')
    manager.show_by_string('protogeni 2 advertisement')
    manager.show_by_schema('http://www.protogeni.net/resources/rspec/2/ad.xsd')
    manager.show_by_schema('http://sorch.netmode.ntua.gr/ws/RSpec/ad.xsd')
