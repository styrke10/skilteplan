"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
"""


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *
import urllib.request
import json
import os, ssl


@qgsfunction(args='auto', group='Custom')
def getNearestAddress(x,y, feature, parent):
    """
    Henter - via en service på Dataforsyningen - den nærmeste (danske) adresse til det punkt, som er defineret af parametrene x og y.<br>
    <h3>Syntax:</h3>
    getNearestAddress( x, y )
    
    <h3>Parametre:</h3>
    <ul>
    <li>x:  X koordinat</li>
    <li>y:  Y koordinat</li>
    </ul>

    <h3>Eksempler:</h3>
    <ul>
      <li>getNearestAddress(507181.02, 6149080.57) -> 'Industrivej Vest 41, 6600 Vejen'</li>
      <li>getNearestAddress($x, $y) -> 'Jernbanegade 27, 6000 Kolding'</li>
    </ul>
    Koordinater skal angives i ETRS89 UTM Zone 32N (EPSG:25832).<br><br>
    """

    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context

    service_url = 'https://api.dataforsyningen.dk/adgangsadresser/reverse?x={}&y={}&srid=25832&struktur=mini'

    url = service_url.format(x,y) 
    urlData = urllib.request.urlopen(url).read()
    jsData = json.loads(urlData.decode('utf-8'))

    return jsData['vejnavn'] + ' ' + jsData['husnr'] + ', ' + jsData['postnr'] + ' ' + jsData['postnrnavn']
