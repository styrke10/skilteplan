"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
"""


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *
import urllib.request
import xml.etree.ElementTree as ET
import json
import os, ssl


@qgsfunction(args='auto', group='Custom')
def getParcelNumber(x,y, token, feature, parent):
    """
    Henter - via en service på Dataforsyningen - den nærmeste (danske) matrikel/jordstykke til det punkt, som er defineret af parametrene x og y.<br>
    <h3>Syntax:</h3>
    getParcelNumber( x, y )
    
    <h3>Parametre:</h3>
    <ul>
    <li>x:  X koordinat</li>
    <li>y:  Y koordinat</li>
    </ul>

    <h3>Eksempler:</h3>
    <ul>
      <li>getParcelNumber(507181.02, 6149080.57, '<token>') -> '9bo, Vejen By, Vejen'</li>
      <li>getParcelNumber($x, $y, '<token>') -> '428b, Kolding Bygrunde'</li>
    </ul>
    Koordinater skal angives i ETRS89 UTM Zone 32N (EPSG:25832).<br><br>
    """

    if not token:
        return None

    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context

    matr_url = 'https://api.dataforsyningen.dk/wfs/MatGaeldendeOgForeloebigWFS_DAF?token={}&table=%22%22&SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&TYPENAMES=mat:Jordstykke_Gaeldende&COUNT=1&SRSNAME=urn:ogc:def:crs:EPSG::25832&BBOX={},{},{},{},urn:ogc:def:crs:EPSG::25832&NAMESPACES=xmlns(mat,http://data.gov.dk/schemas/matrikel/1)&NAMESPACE=xmlns(mat,http://data.gov.dk/schemas/matrikel/1)'

    url = matr_url.format(token,x,y,x,y) 
    urlData = urllib.request.urlopen(url).read()
    
    ns = {'wfs': 'http://www.opengis.net/wfs/2.0', 'mat': 'http://data.gov.dk/schemas/matrikel/1'}
    tree = ET.ElementTree(ET.fromstring(urlData))
    root = tree.getroot()
    
    elavnr = 0
    print(len(root.findall('wfs:member', ns)))
    for member in root.findall('wfs:member', ns):
        for jordstykke in member.findall('mat:Jordstykke_Gaeldende', ns):
            matrnr = jordstykke.find('mat:matrikelnummer', ns).text
            elavnr = jordstykke.find('mat:ejerlavskode', ns).text

    elav_url = 'https://api.dataforsyningen.dk/ejerlav/{}'

    url = elav_url.format(elavnr)
    try:
        urlData = urllib.request.urlopen(url).read()
        jsData = json.loads(urlData.decode('utf-8'))
        elavnavn = jsData['navn']
    except:
        elavnavn = '<ukendt>'

    return matrnr + ', ' + elavnavn
