# -*- coding: utf-8 -*-
"""
/***************************************************************************
 skilteplan_atlas
                                 A QGIS plugin
 Virtuelt lag med ét objekt pr. skilteplan, og et printlayout med atlas
 bygget paa det.

 Det virtuelle lag samler skiltenes geometri pr. planid, saa atlasset faar
 én side pr. skilteplan i stedet for én pr. skilt.
 ***************************************************************************/
"""

import os

from qgis.PyQt.QtXml import QDomDocument
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsPrintLayout,
    QgsReadWriteContext,
    QgsVectorLayer,
    QgsVirtualLayerDefinition,
)

from . import skilteplan_skema as skema


ATLASLAG_NAVN = "Skilteplan atlas"
LAYOUT_NAVN = "Skilteplan"
SKABELON = "skilteplan.qpt"


# --------------------------------------------------------------------------
# Virtuelt lag
# --------------------------------------------------------------------------

def _forespoergsel():
    """
    Ét objekt pr. skilteplan med skiltenes samlede geometri.

    ST_Collect giver et MULTIPOINT, hvis omskrevne rektangel bliver atlassets
    udstraekning. Planer uden skilte udelades - de har ingen geometri at zoome
    til og ville give en tom side.
    """
    return """
        SELECT
            p.planid                AS planid,
            p.navn                  AS navn,
            p.beskrivelse           AS beskrivelse,
            p.startdato             AS startdato,
            p.slutdato              AS slutdato,
            p.kontaktorganisation   AS kontaktorganisation,
            p.kontaktperson         AS kontaktperson,
            p.kontakttelefon        AS kontakttelefon,
            p.kontaktmail           AS kontaktmail,
            COUNT(s.planid)         AS antal_skilte,
            ST_Collect(s.geometry)  AS geometry
        FROM skilteplan AS p
        JOIN skilte AS s ON s.planid = p.planid
        GROUP BY p.planid
    """.strip()


def opretAtlaslag(project, skiltelayer, planlayer, navn=ATLASLAG_NAVN):
    """
    Opretter (eller genskaber) det virtuelle lag og laegger det i projektet.

    Lagene refereres paa id og ikke paa navn, saa de kan hedde hvad som helst
    og omdoebes bagefter uden at laget gaar i stykker.
    """
    for gammelt in project.mapLayersByName(navn):
        project.removeMapLayer(gammelt.id())

    d = QgsVirtualLayerDefinition()
    # To argumenter = referencer til lag, der ligger i projektet. Med et
    # tredje argument opfattes andet argument som en datakildestreng og
    # tredje som providernavn, og laget bliver ugyldigt.
    d.addSource("skilte", skiltelayer.id())
    d.addSource("skilteplan", planlayer.id())
    d.setQuery(_forespoergsel())
    d.setGeometryField("geometry")
    d.setGeometryWkbType(Qgis.WkbType.MultiPoint)
    d.setGeometrySrid(skema.SRID)
    d.setUid("planid")

    uri = d.toString()
    QgsMessageLog.logMessage("Atlaslagets definition: {}".format(uri),
                             tag="skilteplan", level=Qgis.MessageLevel.Info)

    lag = QgsVectorLayer(uri, navn, "virtual")
    if not lag.isValid():
        try:
            aarsag = lag.error().summary()
        except Exception:
            aarsag = "ukendt"
        raise IOError(
            "Det virtuelle atlaslag kunne ikke oprettes.\n\n{}\n\n"
            "Definitionen står i QGIS-loggen under 'skilteplan'.".format(aarsag))

    # Tilfoejes uden for lagtraeet og laegges derefter nederst i roden -
    # det er en hjaelpegeometri, ikke noget man arbejder i
    project.addMapLayer(lag, False)
    project.layerTreeRoot().addLayer(lag)

    QgsMessageLog.logMessage(
        "Atlaslaget '{}' oprettet med {} skilteplaner".format(
            navn, lag.featureCount()),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return lag


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

def _skabelonSti():
    # Skabelonen ligger i data/, ét niveau over core/
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", SKABELON)


def _retAtlaskilde(doc, atlaslag):
    """
    Peger skabelonens atlas paa det netop oprettede lag.

    skilteplan.qpt bærer det dækningslag, den blev gemt med - baade lag-id og
    hele den virtuelle URI med kildelagenes id'er. Uden omskrivning peger
    atlasset paa lag fra et andet projekt.
    """
    rettet = 0
    noder = doc.elementsByTagName("Atlas")
    for i in range(noder.count()):
        el = noder.at(i).toElement()
        if el.isNull():
            continue
        el.setAttribute("coverageLayer", atlaslag.id())
        el.setAttribute("coverageLayerName", atlaslag.name())
        el.setAttribute("coverageLayerSource", atlaslag.publicSource())
        el.setAttribute("coverageLayerProvider", atlaslag.providerType())
        rettet += 1

    QgsMessageLog.logMessage(
        "Atlasdækning i skabelonen sat til '{}' ({} element)".format(
            atlaslag.name(), rettet),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return rettet


def opretLayout(project, atlaslag, navn=LAYOUT_NAVN, overskriv=False):
    """
    Indlaeser printlayoutet fra skabelonen skilteplan.qpt.

    Findes layoutet allerede i projektet, roeres det ikke - brugeren har
    sandsynligvis tilpasset det. Saet overskriv=True for at bygge det forfra.
    """
    manager = project.layoutManager()

    eksisterende = manager.layoutByName(navn)
    if eksisterende is not None:
        if not overskriv:
            QgsMessageLog.logMessage(
                "Layoutet '{}' findes i forvejen og blev ikke ændret".format(navn),
                tag="skilteplan", level=Qgis.MessageLevel.Info)
            return eksisterende
        manager.removeLayout(eksisterende)

    sti = _skabelonSti()
    if not os.path.isfile(sti):
        raise IOError("Layoutskabelonen blev ikke fundet:\n{}".format(sti))

    with open(sti, encoding="utf-8") as f:
        indhold = f.read()

    doc = QDomDocument()
    svar = doc.setContent(indhold)
    if not (svar[0] if isinstance(svar, tuple) else svar):
        raise IOError("Layoutskabelonen kunne ikke fortolkes som XML.")

    _retAtlaskilde(doc, atlaslag)

    layout = QgsPrintLayout(project)
    svar = layout.loadFromTemplate(doc, QgsReadWriteContext())
    ok = svar[1] if isinstance(svar, tuple) and len(svar) > 1 else bool(svar)
    if not ok:
        raise IOError("Layoutskabelonen kunne ikke indlæses.")

    layout.setName(navn)
    manager.addLayout(layout)

    QgsMessageLog.logMessage(
        "Layoutet '{}' indlæst fra {}".format(navn, SKABELON),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return layout


def opretAtlasOgLayout(project, skiltelayer, planlayer):
    """
    Opretter atlaslaget og layoutet. Returnerer (lag, layout).

    Kaster ved fejl, saa kalderen kan vise den - en stille log gjorde det
    svaert at se, at der slet ikke skete noget.
    """
    lag = opretAtlaslag(project, skiltelayer, planlayer)
    return lag, opretLayout(project, lag)
