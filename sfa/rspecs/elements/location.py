from sfa.rspecs.elements.element import Element


class Location(Element):

    fields = [
        'country',
        'longitude',
        'latitude',
        'city',
    ]
