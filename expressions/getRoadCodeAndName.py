"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
"""


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *


@qgsfunction(args='auto', group='Custom', handlesnull=True)
def getRoadCodeAndName(linelayer, fvejkode, fvejnavn, feature, parent):
    """
    Henter vejkode og vejnavn for nærmeste vejsegment i laget linelayer<br><br>
    <h3>Syntax:</h3>
    getVejkodeNavn(linelayer, fvejkode, fvejnavn)
    
    <h3>Parametre:</h3>
    <ul>
    <li>linelayer: Navnet på det linjelag, som indeholder vejmidter m. navn og vejkode.</li>
    <li>fvejkode: Feltnavnet for vejkodefeltet.</li>
    <li>fvejnavn: Feltnavnet for vejnavnefeltet.</li>

    """

    # initializations
    tolerance = 0.1           # search tolerance

    # get linelayer
    layers = QgsProject.instance().mapLayersByName(linelayer)
    if len(layers) == 0:
        return "0004:linjelag ugyldigt '{}'".format(linelayer)
    else:
        lines = layers[0]

    # Check that field names and linelayer are valid
    if not (fvejkode and fvejnavn and lines and feature.hasGeometry()):
        return '0001:felter ugyldige' #None
    
    x = feature.geometry().asPoint().x()
    y = feature.geometry().asPoint().y()

    # get the rectangular search area
    searchRect = QgsRectangle(x - tolerance, y - tolerance,  x + tolerance, y + tolerance)

    # find lines
    found = []
    for line in lines.getFeatures(QgsFeatureRequest().setFilterRect(searchRect)):

        # get the distance to the nearest segment on line
        (dist, res_pnt, v_after, leftOf) = line.geometry().closestSegmentWithContext(feature.geometry().asPoint())

        vejkode = line[fvejkode]
        vejnavn = line[fvejnavn]
        found.append([dist,vejkode,vejnavn])

    # if found were found, use the segment closest to the input point
    if len(found) > 0:
        sort_found = sorted(found, key=lambda tup: tup[0])

        # find attribute values on the CLOSEST segment
        if sort_found[0][0] <= tolerance:
            vejkode = sort_found[0][1]
            vejnavn = sort_found[0][2]
            return '{}:{}'.format(str(vejkode).zfill(4), vejnavn)

        return '0002:ingen linjer indenfor tolerance' #None
    else:
        return '0003:ingen linjer fundet' #None
