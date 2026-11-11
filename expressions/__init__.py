# -*- coding: utf-8 -*-
"""
Udtryksfunktioner til QGIS, registreret under gruppen Custom:

    rotateRoadSign      rotation ud fra naermeste linjesegment
    getRoadCodeAndName  vejkode og vejnavn fra naermeste vejsegment
    getNearestAddress   naermeste adresse via Dataforsyningen
    getParcelNumber     matrikel og ejerlav via Dataforsyningen

Funktionerne registreres, naar modulerne importeres i skilteplan.py, og
afregistreres i unload(). De kan bruges i alle udtryk i QGIS, ogsaa
uden for plugin'et.
"""