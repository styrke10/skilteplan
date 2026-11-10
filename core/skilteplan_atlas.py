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
    QgsMapThemeCollection,
    QgsMessageLog,
    QgsPalLayerSettings,
    QgsPrintLayout,
    QgsProperty,
    QgsReadWriteContext,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsVirtualLayerDefinition,
)

from . import skilteplan_skema as skema


ATLASLAG_NAVN = "Skilteplan atlas"
LAYOUT_NAVN = "Skilteplan"
SKABELON = "skilteplan.qpt"
ATLASSTIL_NAVN = "Atlas - kun aktuel plan"
TEMA_NAVN = "Skilteplan atlas"
KORT_ID = "kort"

# Kun skilte, hvis planid svarer til den aktuelle atlasside. Uden for et
# atlas er @atlas_feature NULL, saa stilarten viser intet i kortvinduet.
ATLASFILTER = "\"planid\" = attribute(@atlas_feature, 'planid')"


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
            "Definitionen staar i QGIS-loggen under 'skilteplan'.".format(aarsag))

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
# Stilart og korttema til atlasset
# --------------------------------------------------------------------------

def _filtreretRenderer(renderer):
    """
    Lægger rendereren ind under en regel med atlasfilteret.

    Rendereren konverteres til regelbaseret, og alle dens regler flyttes ind
    under én overordnet regel, saa symbologien ellers er uaendret.
    """
    konverteret = QgsRuleBasedRenderer.convertFromRenderer(renderer)
    if konverteret is None:
        raise IOError("Skiltelagets renderer kunne ikke konverteres til regelbaseret.")

    gammel_rod = konverteret.rootRule()
    filterregel = QgsRuleBasedRenderer.Rule(None, 0, 0, ATLASFILTER, "Aktuel atlasside")
    for barn in list(gammel_rod.children()):
        filterregel.appendChild(barn.clone())

    rod = QgsRuleBasedRenderer.Rule(None)
    rod.appendChild(filterregel)
    ny = QgsRuleBasedRenderer(rod)
    try:
        konverteret.copyRendererData(ny)  # bevar fx sortering og paintEffect
    except AttributeError:
        pass  # aeldre QGIS uden copyRendererData i Python
    return ny


def _filtrerLabels(lag):
    """Skjuler labels for skilte fra andre planer (kun simple labels)."""
    labeling = lag.labeling()
    if labeling is None or not lag.labelsEnabled():
        return
    if not isinstance(labeling, QgsVectorLayerSimpleLabeling):
        QgsMessageLog.logMessage(
            "Skiltelaget har regelbaserede labels - de filtreres ikke i atlasstilen",
            tag="skilteplan", level=Qgis.MessageLevel.Warning)
        return
    indstillinger = QgsPalLayerSettings(labeling.settings())
    try:
        vis = QgsPalLayerSettings.Property.Show      # QGIS 3.30+
    except AttributeError:
        vis = QgsPalLayerSettings.Show
    egenskaber = indstillinger.dataDefinedProperties()
    egenskaber.setProperty(vis, QgsProperty.fromExpression(ATLASFILTER))
    indstillinger.setDataDefinedProperties(egenskaber)
    lag.setLabeling(QgsVectorLayerSimpleLabeling(indstillinger))


def opretAtlasstil(skiltelayer, navn=ATLASSTIL_NAVN):
    """
    Tilfoejer en ekstra stilart til skiltelaget, der kun viser skiltene paa
    den aktuelle atlasside. Den aktive stilart er uaendret bagefter.

    Stilarten bygges som en kopi af den aktive, saa den foelger skilte.qml.
    """
    sm = skiltelayer.styleManager()

    # Den aktive stilart kan ikke fjernes - skift vaek fra den foerst
    if sm.currentStyle() == navn:
        andre = [s for s in sm.styles() if s != navn]
        if andre:
            sm.setCurrentStyle(andre[0])
    if navn in sm.styles():
        sm.removeStyle(navn)

    original = sm.currentStyle()
    if not sm.addStyleFromLayer(navn):
        raise IOError("Stilarten '{}' kunne ikke oprettes.".format(navn))

    # Aendringerne gemmes i den nye stilart, naar der skiftes tilbage
    sm.setCurrentStyle(navn)
    try:
        skiltelayer.setRenderer(_filtreretRenderer(skiltelayer.renderer()))
        _filtrerLabels(skiltelayer)
    finally:
        sm.setCurrentStyle(original)
    skiltelayer.triggerRepaint()

    QgsMessageLog.logMessage(
        "Stilarten '{}' tilfoejet til '{}'".format(navn, skiltelayer.name()),
        tag="skilteplan", level=Qgis.MessageLevel.Info)


def opretKorttema(project, skiltelayer, atlaslag, navn=TEMA_NAVN,
                  stilnavn=ATLASSTIL_NAVN):
    """
    Korttema med de lag, der er synlige nu, hvor skiltelaget bruger
    atlasstilen. Layoutets hovedkort foelger temaet.
    """
    rekord = QgsMapThemeCollection.MapThemeRecord()
    skilte_med = False
    for node in project.layerTreeRoot().findLayers():
        lag = node.layer()
        if lag is None or lag.id() == atlaslag.id():
            continue
        er_skilte = lag.id() == skiltelayer.id()
        if not (node.isVisible() or er_skilte):
            continue
        lr = QgsMapThemeCollection.MapThemeLayerRecord(lag)
        if er_skilte:
            lr.usingCurrentStyle = True
            lr.currentStyle = stilnavn
            skilte_med = True
        rekord.addLayerRecord(lr)

    if not skilte_med:
        raise IOError("Skiltelaget ligger ikke i lagtraeet og kan ikke komme med i korttemaet.")

    temaer = project.mapThemeCollection()
    if temaer.hasMapTheme(navn):
        temaer.update(navn, rekord)
    else:
        temaer.insert(navn, rekord)

    QgsMessageLog.logMessage(
        "Korttemaet '{}' oprettet med {} lag".format(navn, len(rekord.layerRecords())),
        tag="skilteplan", level=Qgis.MessageLevel.Info)


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
        "Atlasdaekning i skabelonen sat til '{}' ({} element)".format(
            atlaslag.name(), rettet),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return rettet


def _saetKorttema(doc, tema=TEMA_NAVN):
    """Faar hovedkortet i skabelonen til at foelge korttemaet."""
    noder = doc.elementsByTagName("LayoutItem")
    for i in range(noder.count()):
        el = noder.at(i).toElement()
        if el.isNull() or el.attribute("id") != KORT_ID:
            continue
        el.setAttribute("followPreset", "true")
        el.setAttribute("followPresetName", tema)
        return True
    QgsMessageLog.logMessage(
        "Kortet '{}' blev ikke fundet i skabelonen - korttemaet er ikke sat".format(KORT_ID),
        tag="skilteplan", level=Qgis.MessageLevel.Warning)
    return False


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
                "Layoutet '{}' findes i forvejen og blev ikke aendret".format(navn),
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
    _saetKorttema(doc)

    layout = QgsPrintLayout(project)
    svar = layout.loadFromTemplate(doc, QgsReadWriteContext())
    ok = svar[1] if isinstance(svar, tuple) and len(svar) > 1 else bool(svar)
    if not ok:
        raise IOError("Layoutskabelonen kunne ikke indlaeses.")

    layout.setName(navn)
    manager.addLayout(layout)

    QgsMessageLog.logMessage(
        "Layoutet '{}' indlaest fra {}".format(navn, SKABELON),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return layout


def opretAtlasOgLayout(project, skiltelayer, planlayer):
    """
    Opretter atlaslaget og layoutet. Returnerer (lag, layout).

    Kaster ved fejl, saa kalderen kan vise den - en stille log gjorde det
    svaert at se, at der slet ikke skete noget.
    """
    lag = opretAtlaslag(project, skiltelayer, planlayer)
    opretAtlasstil(skiltelayer)
    opretKorttema(project, skiltelayer, lag)
    return lag, opretLayout(project, lag)
