# -*- coding: utf-8 -*-
"""
/***************************************************************************
 skilteplan_skema
                                 A QGIS plugin
 Faelles skemadefinition for skilteplan-tabellerne.

 Dette modul er ENESTE kilde til feltdefinitionerne. Alt andet - oprettelse
 af GeoPackage, oprettelse i PostGIS, generering af skilteplan.sql og
 validering af lag, som brugeren selv har hentet ind i projektet - udledes
 herfra. Skal et felt tilfoejes eller aendres, sker det i SKEMA nedenfor og
 ingen andre steder.
 ***************************************************************************/
"""

import os

from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    Qgis,
    QgsField,
    QgsFields,
    QgsMessageLog,
    QgsProject,
    QgsProviderRegistry,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)


# --------------------------------------------------------------------------
# Skemadefinition
#
# Felttyper angives som QMetaType.Type. Det er API'et fra QGIS 3.38 og frem,
# og det eneste der findes i QGIS 4 - QVariant-typerne forsvinder med Qt6.
# --------------------------------------------------------------------------

SRID = 25832
CRS_AUTHID = "EPSG:{}".format(SRID)

# Rollenavne. 'skilte manuelt' er IKKE en selvstaendig tabel, men en filtreret
# visning af 'skilte' (manuelrotation = true), og optraeder derfor ikke her.
ROLLE_SKILTE = "skilte"
ROLLE_SKILTETYPER = "skiltetyper"
ROLLE_SKILTEPLAN = "skilteplan"

ROLLER = (ROLLE_SKILTE, ROLLE_SKILTETYPER, ROLLE_SKILTEPLAN)

# Klientsidig autonummerering af skilteplan.planid. Saettes som
# QgsDefaultValue paa skilteplan-laget, saa nye planer faar et nummer
# uanset om de ligger i PostGIS, GeoPackage eller FileGDB.
DEFAULT_PLANID = 'coalesce(maximum("planid"), 0) + 1' 

# Felter fra 'skilteplan', der foejes til skiltelagene gennem joinet, saa de
# er tilgaengelige i printlayout - ogsaa naar layoutet drives af skiltelaget
# via atlas. Noeglefeltet selv udelades; det ligger allerede i skilte.planid.
# Defaultvaerdi for rotation paa det samlede skiltelag.
#
# Udtrykket saettes med applyOnUpdate=True, saa rotationen foelger med, naar
# et skilt flyttes. Uden if-testen ville den genberegning ogsaa overskrive den
# vinkel, brugeren selv har tastet paa et manuelt roteret skilt - og det var
# netop derfor plugin'et tidligere havde to separate skiltelag.
DEFAULT_ROTATION = (
    'if("manuelrotation", "rotation", '
    'rotateRoadSign( array(@snaplag), 0.1, "retning"))'
)

JOIN_FELTER = [
    "beskrivelse", "startdato", "slutdato",
    "kontaktorganisation", "kontaktperson", "kontakttelefon", "kontaktmail",
]


def _felt(navn, qtype, laengde=0, sqltype=None, noegle=False, valgfri=False):
    """
    Et enkelt feltdefinition. sqltype bruges kun ved SQL-generering.

    valgfri=True betyder, at feltet oprettes i nye tabeller, men at et
    eksisterende lag uden feltet stadig godkendes (med en advarsel). Bruges
    til felter, der er kommet til efter version 1.0.
    """
    return {
        "navn": navn,
        "qtype": qtype,
        "laengde": laengde,
        "sqltype": sqltype,
        "noegle": noegle,
        "valgfri": valgfri,
    }


SKEMA = {
    ROLLE_SKILTE: {
        "geometri": Qgis.WkbType.Point,
        "geomkolonne": "geom",
        "beskrivelse": "Skiltepunkter",
        "felter": [
            _felt("id", QMetaType.Type.Int, sqltype="serial", noegle=True),
            _felt("planid", QMetaType.Type.Int, sqltype="integer"),
            _felt("rotation", QMetaType.Type.Double, sqltype="double precision"),
            _felt("retning", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("offset", QMetaType.Type.Double, sqltype="double precision"),
            _felt("dobbeltsidet", QMetaType.Type.Bool, sqltype="boolean"),
            _felt("type_forside", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("utype_forside1", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("utype_forside2", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("type_bagside", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("utype_bagside1", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("utype_bagside2", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("manuelrotation", QMetaType.Type.Bool, sqltype="boolean"),
            _felt("vejnavn", QMetaType.Type.QString, 30, "character varying(30)"),
            _felt("vejkode", QMetaType.Type.QString, 4, "character varying(4)"),
            _felt("adresse", QMetaType.Type.QString, 80, "character varying(80)"),
            # Fandtes i den leverede GeoPackage, men manglede i skilteplan.sql.
            # skilte.qml refererer til dem begge.
            _felt("matrikel", QMetaType.Type.QString, 80, "character varying(80)"),
            _felt("vejkodenavn", QMetaType.Type.QString, 40, "character varying(40)"),
            _felt("faktor", QMetaType.Type.Int, sqltype="integer"),
        ],
    },
    ROLLE_SKILTETYPER: {
        "geometri": Qgis.WkbType.NoGeometry,
        "geomkolonne": None,
        "beskrivelse": "Skiltebibliotek",
        "felter": [
            _felt("id", QMetaType.Type.Int, sqltype="serial", noegle=True),
            _felt("skiltenavn", QMetaType.Type.QString, 10, "character varying(10)"),
            _felt("skiltebeskrivelse", QMetaType.Type.QString, 50, "character varying(50)"),
            _felt("niveau", QMetaType.Type.Int, sqltype="integer"),
            _felt("bredde", QMetaType.Type.Double, sqltype="double precision"),
            _felt("hojde", QMetaType.Type.Double, sqltype="double precision"),
            # Inaktive skilte bliver i biblioteket, men vises ikke i
            # rullelisterne, naar der vaelges skilte til et punkt. NULL
            # regnes som aktiv. I Esri-geodatabaser, der ikke har boolean,
            # kan feltet vaere et heltal med 0/1.
            _felt("inaktiv", QMetaType.Type.Bool, sqltype="boolean DEFAULT false",
                  valgfri=True),
        ],
    },
    ROLLE_SKILTEPLAN: {
        "geometri": Qgis.WkbType.NoGeometry,
        "geomkolonne": None,
        "beskrivelse": "Skilteplaner",
        "felter": [
            # Hed tidligere 'id'. Omdoebt til 'planid' saa den ikke forveksles
            # med providerens raekkenoegle (fid i GeoPackage, OBJECTID i Esri).
            # Matcher navnet paa fremmednoeglen i 'skilte'.
            #
            # Bevidst 'integer' og IKKE 'serial': serial autonummererer kun i
            # PostGIS. Vaerdien saettes i stedet klientsiden af QGIS gennem
            # DEFAULT_PLANID, saa den opfoerer sig ens i alle backends.
            _felt("planid", QMetaType.Type.Int, sqltype="integer NOT NULL", noegle=True),
            _felt("navn", QMetaType.Type.QString, 50, "character varying(50)"),
            # Ingen laengdebegraensning - beskrivelsen bruges i printlayout og
            # blev afkortet ved 200 tegn.
            _felt("beskrivelse", QMetaType.Type.QString, 0, "text"),
            _felt("startdato", QMetaType.Type.QDate, sqltype="date"),
            _felt("slutdato", QMetaType.Type.QDate, sqltype="date"),
            # Kontaktoplysninger til sidefod/titelblok i printlayout
            _felt("kontaktorganisation", QMetaType.Type.QString, 100, "character varying(100)"),
            _felt("kontaktperson", QMetaType.Type.QString, 80, "character varying(80)"),
            _felt("kontakttelefon", QMetaType.Type.QString, 20, "character varying(20)"),
            _felt("kontaktmail", QMetaType.Type.QString, 100, "character varying(100)"),
        ],
    },
}


# --------------------------------------------------------------------------
# Opslag
# --------------------------------------------------------------------------

def felter(rolle):
    """Feltdefinitionerne for en rolle (raa dicts)."""
    if rolle not in SKEMA:
        raise ValueError("Ukendt rolle: {}".format(rolle))
    return SKEMA[rolle]["felter"]


def feltnavne(rolle):
    return [f["navn"] for f in felter(rolle)]


def noeglefelt(rolle):
    """Navnet paa forretningsnoeglen - ikke providerens raekkenoegle."""
    for f in felter(rolle):
        if f["noegle"]:
            return f["navn"]
    return None


def geometritype(rolle):
    return SKEMA[rolle]["geometri"]


def harGeometri(rolle):
    return geometritype(rolle) != Qgis.WkbType.NoGeometry


def qgsFields(rolle):
    """Feltdefinitionerne som QgsFields."""
    fields = QgsFields()
    for f in felter(rolle):
        if f["laengde"]:
            fields.append(QgsField(f["navn"], f["qtype"], "", f["laengde"]))
        else:
            fields.append(QgsField(f["navn"], f["qtype"]))
    return fields


# --------------------------------------------------------------------------
# Oprettelse
# --------------------------------------------------------------------------

def hukommelseslag(rolle, navn=None):
    """Tomt hukommelseslag med rollens skema. Grundstenen for al oprettelse."""
    if harGeometri(rolle):
        uri = "{}?crs={}".format(
            QgsWkbTypes.displayString(geometritype(rolle)), CRS_AUTHID)
    else:
        uri = "None"

    lag = QgsVectorLayer(uri, navn or rolle, "memory")
    if not lag.isValid():
        raise IOError("Kunne ikke oprette hukommelseslag for '{}'".format(rolle))

    provider = lag.dataProvider()
    provider.addAttributes(qgsFields(rolle).toList())
    lag.updateFields()
    return lag


def opretGeopackage(sti, roller=None, overskriv=False):
    """
    Opretter (eller udvider) en GeoPackage med de angivne roller.

    Returnerer stien til GeoPackage'en. Kaster IOError ved fejl.
    OGR tilfoejer selv en 'fid'-kolonne som raekkenoegle; skemaets egne
    noeglefelter ligger ved siden af som almindelige heltalskolonner.
    """
    roller = roller or ROLLER

    if os.path.exists(sti) and not overskriv:
        # Nye lag foejes til den eksisterende fil
        foerste_handling = QgsVectorFileWriter.CreateOrOverwriteLayer
    else:
        foerste_handling = QgsVectorFileWriter.CreateOrOverwriteFile

    ctx = QgsProject.instance().transformContext()

    for i, rolle in enumerate(roller):
        lag = hukommelseslag(rolle)

        opt = QgsVectorFileWriter.SaveVectorOptions()
        opt.driverName = "GPKG"
        opt.layerName = rolle
        opt.fileEncoding = "UTF-8"
        opt.actionOnExistingFile = (
            foerste_handling if i == 0
            else QgsVectorFileWriter.CreateOrOverwriteLayer)
        if harGeometri(rolle):
            opt.layerOptions = ["GEOMETRY_NAME={}".format(
                SKEMA[rolle]["geomkolonne"])]

        resultat = QgsVectorFileWriter.writeAsVectorFormatV3(lag, sti, ctx, opt)

        # V3 returnerer (fejlkode, besked, nytFilnavn, nytLagnavn)
        fejlkode = resultat[0]
        besked = resultat[1] if len(resultat) > 1 else ""
        if fejlkode != QgsVectorFileWriter.NoError:
            raise IOError("Kunne ikke skrive '{}' til {}: {}".format(
                rolle, sti, besked))

    QgsMessageLog.logMessage(
        "GeoPackage oprettet: {} ({})".format(sti, ", ".join(roller)),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return sti


def opretPostgis(forbindelsesnavn, skema="skilteplan", roller=None, overskriv=False):
    """
    Opretter tabellerne i PostGIS via en gemt QGIS-forbindelse.

    Bruger providerens forbindelses-API frem for QgsVectorLayerExporter, saa
    vi faar serial-noegler, primaernoeglebetingelser og GiST-indeks praecis
    som i den genererede SQL.
    """
    md = QgsProviderRegistry.instance().providerMetadata("postgres")
    if md is None:
        raise IOError("PostgreSQL-provideren er ikke tilgængelig i denne QGIS-installation")

    forbindelse = md.findConnection(forbindelsesnavn)
    if forbindelse is None:
        raise IOError("PostGIS-forbindelsen '{}' findes ikke".format(forbindelsesnavn))

    sql = genererSql(skema=skema, roller=roller, drop=overskriv)

    # Én saetning ad gangen. Ikke alle providere udfoerer flere saetninger i
    # ét kald, og fejler noget, kan vi sige praecis hvad der gik galt.
    # Scriptet er genereret her i modulet, saa der er ingen semikolonner
    # inde i strenge at tage hoejde for.
    saetninger = [x.strip() for x in sql.split(";") if x.strip()]
    for nr, saetning in enumerate(saetninger, 1):
        try:
            forbindelse.executeSql(saetning)
        except Exception as e:
            raise IOError(
                "Fejl i saetning {} af {}:\n\n{}\n\n{}".format(
                    nr, len(saetninger), saetning.split("\n")[0], e))

    QgsMessageLog.logMessage(
        "PostGIS: {} sætninger udført i skemæt '{}' på '{}'".format(
            len(saetninger), skema, forbindelsesnavn),
        tag="skilteplan", level=Qgis.MessageLevel.Info)
    return skema


def genererSql(skema="skilteplan", roller=None, drop=False):
    """
    Genererer CREATE-scriptet ud fra SKEMA. Erstatter den haandholdte
    skilteplan.sql, saa skemaet kun findes ét sted.
    """
    roller = roller or ROLLER
    linjer = ["CREATE SCHEMA IF NOT EXISTS {};".format(skema), ""]

    for rolle in roller:
        d = SKEMA[rolle]
        if drop:
            linjer.append("DROP TABLE IF EXISTS {}.{};".format(skema, rolle))
            linjer.append("")

        kolonner = []
        for f in d["felter"]:
            navn = '"{}"'.format(f["navn"]) if f["navn"] in ("offset",) else f["navn"]
            kolonner.append("    {} {}".format(navn, f["sqltype"]))

        if d["geomkolonne"]:
            kolonner.insert(1, "    {} geometry({},{})".format(
                d["geomkolonne"],
                QgsWkbTypes.displayString(d["geometri"]),
                SRID))

        noegle = noeglefelt(rolle)
        if noegle:
            kolonner.append("    CONSTRAINT {}_pkey PRIMARY KEY ({})".format(rolle, noegle))

        linjer.append("CREATE TABLE IF NOT EXISTS {}.{}".format(skema, rolle))
        linjer.append("(")
        linjer.append(",\n".join(kolonner))
        linjer.append(");")
        linjer.append("")

        if d["geomkolonne"]:
            linjer.append("CREATE INDEX IF NOT EXISTS sidx_{}_{}".format(
                rolle, d["geomkolonne"]))
            linjer.append("    ON {}.{} USING gist".format(skema, rolle))
            linjer.append("    ({});".format(d["geomkolonne"]))
            linjer.append("")

    return "\n".join(linjer)


# --------------------------------------------------------------------------
# Validering
# --------------------------------------------------------------------------

# Grove typefamilier. Providere er ikke enige om detaljerne (Int vs. LongLong,
# String uden laengde i GPKG), saa vi sammenligner familie og ikke andet.
_FAMILIER = {
    QMetaType.Type.Int: "tal",
    QMetaType.Type.LongLong: "tal",
    QMetaType.Type.UInt: "tal",
    QMetaType.Type.ULongLong: "tal",
    QMetaType.Type.Double: "tal",
    QMetaType.Type.QString: "tekst",
    QMetaType.Type.Bool: "bool",
    QMetaType.Type.QDate: "dato",
    QMetaType.Type.QDateTime: "dato",
}


def _familie(qtype):
    return _FAMILIER.get(qtype, "ukendt")


class Valideringsresultat(object):
    """Samlet resultat af en lagvalidering."""

    def __init__(self, rolle):
        self.rolle = rolle
        self.fejl = []
        self.advarsler = []

    @property
    def ok(self):
        return not self.fejl

    def __str__(self):
        dele = []
        if self.fejl:
            dele.append("Fejl:\n  - " + "\n  - ".join(self.fejl))
        if self.advarsler:
            dele.append("Advarsler:\n  - " + "\n  - ".join(self.advarsler))
        return "\n\n".join(dele) if dele else "Laget er i orden."


def validerLag(lag, rolle):
    """
    Kontrollerer at et lag, brugeren selv har hentet ind i projektet, kan
    udfylde den paagaeldende rolle.

    Manglende kolonner er fejl - symbologien og defaultvaerdierne slaar op i
    dem, og et lag uden dem giver en tom eller forkert skilteplan uden nogen
    synlig fejlmeddelelse. Typeafvigelser og CRS er advarsler.
    """
    res = Valideringsresultat(rolle)

    if rolle not in SKEMA:
        res.fejl.append("Ukendt rolle '{}'".format(rolle))
        return res

    if lag is None:
        res.fejl.append("Intet lag valgt")
        return res

    if not lag.isValid():
        res.fejl.append("Laget '{}' er ikke gyldigt - kontroller datakilden".format(lag.name()))
        return res

    # Geometri
    if harGeometri(rolle):
        if lag.geometryType() != Qgis.GeometryType.Point:
            res.fejl.append("'{}' skal være et punktlag (er: {})".format(
                rolle, QgsWkbTypes.geometryDisplayString(lag.geometryType())))
    else:
        if lag.geometryType() != Qgis.GeometryType.Null:
            res.advarsler.append(
                "'{}' forventes uden geometri, men laget har geometri - "
                "det forhindrer ikke brug".format(rolle))

    # Koordinatsystem
    if harGeometri(rolle):
        authid = lag.crs().authid()
        if authid != CRS_AUTHID:
            res.advarsler.append(
                "Laget er i {} og ikke {}. Rotation og offset regnes i meter "
                "og bliver forkerte i et geografisk koordinatsystem.".format(
                    authid or "ukendt CRS", CRS_AUTHID))

    # Felter
    tilstede = {f.name().lower(): f for f in lag.fields()}
    manglende = []
    for fdef in felter(rolle):
        fundet = tilstede.get(fdef["navn"].lower())
        if fundet is None:
            if fdef.get("valgfri"):
                res.advarsler.append(
                    "Det valgfrie felt '{}' mangler i '{}'. Tilføj det for at "
                    "få den tilhørende funktion.".format(fdef["navn"], lag.name()))
            else:
                manglende.append(fdef["navn"])
            continue

        vent = _familie(fdef["qtype"])
        har = _familie(fundet.type())
        if vent != har and "ukendt" not in (vent, har):
            res.advarsler.append(
                "Feltet '{}' er af typen {} men forventes som {}".format(
                    fdef["navn"], har, vent))

    if manglende:
        res.fejl.append("Manglende kolonner i '{}': {}".format(
            lag.name(), ", ".join(manglende)))

    return res
