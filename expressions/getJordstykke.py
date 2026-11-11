"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments

Finder det jordstykke (matrikel), som et punkt ligger på.
Bruger Datafordelerens GraphQL-tjeneste for Matriklen (MAT v2):
    MAT_Lodflade (geometri)  ->  MAT_Jordstykke  ->  MAT_Ejerlav

Opsætning:
    Opret en global QGIS-variabel 'dar_api_key' med din Datafordeler API-nøgle
    (Indstillinger -> Indstillinger... -> Variabler). Samme nøgle som til
    getNearestAddress - den skal blot også have adgang til MAT-tjenesten.
"""

from qgis.core import (qgsfunction, QgsExpressionContextUtils, QgsMessageLog, Qgis,
                       QgsNetworkAccessManager)
from qgis.PyQt.QtCore import QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from datetime import datetime, timezone
import urllib.parse
import json
import re


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
matGraphqlUrl = 'https://graphql.datafordeler.dk/MAT/v2'
darGlobalVarName = 'dar_api_key'            # navn på global QGIS-variabel
requestTimeout = 30                       # sekunder
# MAT-status er tekst (fx 'Gældende', 'Foreløbig', 'Historisk'). Alt der matcher
# dette mønster sorteres fra; øvrige (gældende/foreløbige) beholdes.
inactiveStatusPattern = re.compile(r'histor|nedlag|afregist|slettet|henlag', re.IGNORECASE)

logTag = 'getJordstykke'
jordstykkeCache = {}                      # (x, y) afrundet til cm -> matrikeltekst
ejerlavCache = {}                         # ejerlav-id -> (ejerlavskode, ejerlavsnavn)


# ---------------------------------------------------------------------------
# GraphQL-forespørgsler
# ---------------------------------------------------------------------------
lodfladeQuery = """
query ($t: DafDateTime!, $wkt: String!) {
  MAT_Lodflade(first: 10, virkningstid: $t, registreringstid: $t,
               where: { geometri: { intersects: { wkt: $wkt, crs: 25832 } } }) {
    nodes { id_lokalId jordstykkeLokalId status }
  }
}
"""

jordstykkeQuery = """
query ($t: DafDateTime!, $ids: [String!]) {
  MAT_Jordstykke(first: 100, virkningstid: $t, registreringstid: $t,
                 where: { id_lokalId: { in: $ids } }) {
    nodes { id_lokalId matrikelnummer ejerlavLokalId status }
  }
}
"""

ejerlavQuery = """
query ($t: DafDateTime!, $id: String!) {
  MAT_Ejerlav(first: 1, virkningstid: $t, registreringstid: $t,
              where: { id_lokalId: { eq: $id } }) {
    nodes { ejerlavskode ejerlavsnavn }
  }
}
"""


# ---------------------------------------------------------------------------
# Hjælpefunktioner
# ---------------------------------------------------------------------------
def getApiKey():
    apiKey = QgsExpressionContextUtils.globalScope().variable(darGlobalVarName)
    if not apiKey:
        raise RuntimeError(f"Global QGIS-variabel '{darGlobalVarName}' med Datafordeler API-nøgle mangler")
    return str(apiKey)


def runGraphql(query, variables):
    # Laver GraphQL request via QGIS' netværkslag (respekterer proxy, SSL- og
    # autentificeringsindstillinger og vises i QGIS' netværkslogger)
    url = QUrl(f"{matGraphqlUrl}?{urllib.parse.urlencode({'apiKey': getApiKey()})}")
    if url.scheme() != 'https':
        raise RuntimeError(f'Ugyldigt URL-skema: {url.scheme()}')

    request = QNetworkRequest(url)
    request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
    request.setTransferTimeout(requestTimeout * 1000)
    body = QByteArray(json.dumps({'query': query, 'variables': variables}).encode('utf-8'))

    # blockingPost er trådsikker og kan kaldes fra QGIS' baggrundstråde (fx rendering)
    reply = QgsNetworkAccessManager.instance().blockingPost(request, body)
    content = bytes(reply.content()).decode('utf-8', errors='replace')

    if reply.error() != QNetworkReply.NetworkError.NoError:
        # GraphQL-fejl returneres ofte som HTTP 400 med forklaringen i body
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        raise RuntimeError(f'HTTP {status}: {content or reply.errorString()}')

    result = json.loads(content)
    if result.get('errors'):
        raise RuntimeError('; '.join(e.get('message', str(e)) for e in result['errors']))
    return result['data']


def isActive(node):
    status = node.get('status')
    return status is None or not inactiveStatusPattern.search(str(status))


def getEjerlav(ejerlavId, timeStamp):
    if ejerlavId not in ejerlavCache:
        nodes = runGraphql(ejerlavQuery, {'t': timeStamp, 'id': ejerlavId})['MAT_Ejerlav']['nodes'] or []
        ejerlavCache[ejerlavId] = (nodes[0]['ejerlavskode'], nodes[0]['ejerlavsnavn']) if nodes else ('', '')
    return ejerlavCache[ejerlavId]


def formatJordstykke(jordstykke, timeStamp):
    ejerlavskode, ejerlavsnavn = getEjerlav(jordstykke['ejerlavLokalId'], timeStamp)
    return f"{jordstykke['matrikelnummer'] or ''} {ejerlavsnavn}".strip()


def lookupJordstykke(x, y):
    timeStamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # 1) Find lodflade(r), som punktet ligger i
    pointWkt = f'POINT ({x} {y})'
    lodflader = runGraphql(lodfladeQuery, {'t': timeStamp, 'wkt': pointWkt})['MAT_Lodflade']['nodes'] or []
    jordstykkeIds = []
    for lodflade in lodflader:
        jordstykkeId = lodflade.get('jordstykkeLokalId')
        if isActive(lodflade) and jordstykkeId and jordstykkeId not in jordstykkeIds:
            jordstykkeIds.append(jordstykkeId)
    if not jordstykkeIds:
        return None   # fx punkt i havet eller på umatrikuleret areal

    # 2) Hent jordstykkerne
    jordstykker = runGraphql(jordstykkeQuery, {'t': timeStamp, 'ids': jordstykkeIds})['MAT_Jordstykke']['nodes'] or []
    jordstykker = [j for j in jordstykker if isActive(j)]
    if not jordstykker:
        return None

    # 3) Formatér. Ligger punktet præcist på et skel, rammer det flere jordstykker -
    #    de returneres så alle, adskilt af ' / '
    if len(jordstykker) > 1:
        QgsMessageLog.logMessage(f'Punktet ({x}, {y}) ligger på skel mellem {len(jordstykker)} jordstykker',
                                 logTag, Qgis.MessageLevel.Info)
    texts = sorted({formatJordstykke(j, timeStamp) for j in jordstykker})
    return ' / '.join(texts)


# ---------------------------------------------------------------------------
# QGIS funktionen
# ---------------------------------------------------------------------------
@qgsfunction(args='auto', group='Custom')
def getJordstykke(x, y, feature, parent):
    """
    Henter - via Datafordelerens GraphQL-tjeneste for Matriklen (MAT) - det jordstykke (matrikelnummer og ejerlav), som punktet defineret af parametrene x og y ligger på.<br>
    <h3>Syntax:</h3>
    getJordstykke( x, y )

    <h3>Parametre:</h3>
    <ul>
    <li>x:  X koordinat</li>
    <li>y:  Y koordinat</li>
    </ul>

    <h3>Eksempler:</h3>
    <ul>
      <li>getJordstykke(507181.02, 6149080.57) -> '12a Vejen By, Vejen'</li>
      <li>getJordstykke($x, $y) -> '345b Kolding Bygrunde'</li>
    </ul>
    Returnerer NULL, hvis punktet ikke ligger på et jordstykke (fx i havet).
    Ligger punktet præcist på et skel, returneres alle berørte jordstykker adskilt af ' / '.<br>
    Koordinater skal angives i ETRS89 UTM Zone 32N (EPSG:25832).<br>
    Kræver den globale variabel <b>'dar_api_key'</b> med en Datafordeler API-nøgle.<br><br>
    """

    if x is None or y is None:
        return None

    cacheKey = (round(float(x), 2), round(float(y), 2))
    if cacheKey in jordstykkeCache:
        return jordstykkeCache[cacheKey]

    try:
        result = lookupJordstykke(float(x), float(y))
    except Exception as e:
        parent.setEvalErrorString(f'getJordstykke: {e}')
        QgsMessageLog.logMessage(str(e), logTag, Qgis.MessageLevel.Critical)
        return None

    jordstykkeCache[cacheKey] = result
    return result
