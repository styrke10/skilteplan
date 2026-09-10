"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
"""


from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.core import *
from qgis.gui import *
import sys
import os, ssl
import math


@qgsfunction(args='auto', group='Custom', handlesnull=True)
def rotateRoadSign(linelayers, tolerance, directional, feature, parent):
    """
    Rotates a point symbol according to the underlying line segment in line layers specified in the list 'linelayers'.
    If no segment is found, a value of -360 is returned.
    """

    # initializations
    if tolerance is None: tolerance = 0.1           # search tolerance
    if directional is None: directional = 'none'    # consider direction?
    #feedback = QgsProcessingFeedback()
    
    for linelayer in linelayers:
        # get linelayer
        lines = QgsProject.instance().mapLayersByName(linelayer.strip())[0]

        x = feature.geometry().asPoint().x()
        y = feature.geometry().asPoint().y()

        # get the rectangular search area
        searchRect = QgsRectangle(x - tolerance, y - tolerance,  x + tolerance, y + tolerance)

        # find lines
        found = []
        distance = QgsDistanceArea()
        for line in lines.getFeatures(QgsFeatureRequest().setFilterRect(searchRect)):

            # get the distance to the nearest segment on line and the vertex ending this (and place on left or right side - not used)
            (dist, res_pnt, v_after, leftOf) = line.geometry().closestSegmentWithContext(feature.geometry().asPoint())

            # if we are very close to a vertex and not on the last one, the angle should be calculated from previous and next vertex
            if distance.measureLine(feature.geometry().asPoint(), QgsPointXY(line.geometry().vertexAt(v_after))) <= tolerance and not (line.geometry().vertexAt(v_after+1)).isEmpty():
                p1 = line.geometry().vertexAt(v_after+1)   # next vertex and one
            else:
                p1 = line.geometry().vertexAt(v_after)   # next vertex after point
            p2 = line.geometry().vertexAt(v_after-1) # previous vertex
            found.append([dist,p1,p2])

        # if found were found, use the segment closest to the input point
        if len(found) > 0:
            sort_found = sorted(found, key=lambda tup: tup[0])
            p1 = sort_found[0][1]
            p2 = sort_found[0][2]

            # calculate bearing
            if sort_found[0][0] <= tolerance:  # only rotate points within tolerance of lines
                angle = math.degrees(math.atan2(p1.x() - p2.x(), p1.y() - p2.y()))
                angle = (angle + 360) if angle < 0 else angle
                geom = feature.geometry()
                
                if directional == 'none':  ## if direction shouldn't be considered, we always place the symbol turning nicely upwards
                    angle = (angle % 360) if math.cos(math.radians(angle % 360)) > 0 else ((angle % 360)-180)
                elif directional == 'left':
                    angle = (angle + 180) % 360

                return round(angle,2)
    
    return -360

