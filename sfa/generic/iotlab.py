from sfa.generic import Generic

import sfa.server.sfaapi


class iotlab (Generic):

    # use the standard api class
    def api_class(self):
        return sfa.server.sfaapi.SfaApi

    # the importer class
    def importer_class(self):
        import sfa.importer.iotlabimporter
        return sfa.importer.iotlabimporter.IotLabImporter

    # the manager classes for the server-side services
    def registry_manager_class(self):
        import sfa.managers.registry_manager
        return sfa.managers.registry_manager.RegistryManager

    def aggregate_manager_class(self):
        import sfa.managers.aggregate_manager
        return sfa.managers.aggregate_manager.AggregateManager

    def driver_class(self):
        import sfa.iotlab.iotlabdriver
        return sfa.iotlab.iotlabdriver.IotLabDriver
