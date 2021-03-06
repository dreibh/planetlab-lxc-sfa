class Element(dict):

    fields = {}

    def __init__(self, fields=None, element=None, keys=None):
        if fields is None:
            fields = {}
        self.element = element
        dict.__init__(self, dict.fromkeys(self.fields))
        if not keys:
            keys = list(fields.keys())
        for key in keys:
            if key in fields:
                self[key] = fields[key]

    def __getattr__(self, name):
        if hasattr(self.__dict__, name):
            return getattr(self.__dict__, name)
        elif hasattr(self.element, name):
            return getattr(self.element, name)
        else:
            raise AttributeError("class Element of type {} has no attribute {}"
                                 .format(self.__class__.__name__, name))
