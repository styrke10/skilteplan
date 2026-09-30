-- GENERERET FIL - rediger ikke direkte.
-- Skemaet defineres i skilteplan_skema.py; regenerer med
--   python -c "import skilteplan_skema as s; print(s.genererSql(drop=True))"

CREATE SCHEMA IF NOT EXISTS skilteplan;

DROP TABLE IF EXISTS skilteplan.skilte;

CREATE TABLE IF NOT EXISTS skilteplan.skilte
(
    id serial,
    geom geometry(Point,25832),
    planid integer,
    rotation double precision,
    retning character varying(10),
    "offset" double precision,
    dobbeltsidet boolean,
    type_forside character varying(10),
    utype_forside1 character varying(10),
    utype_forside2 character varying(10),
    type_bagside character varying(10),
    utype_bagside1 character varying(10),
    utype_bagside2 character varying(10),
    manuelrotation boolean,
    vejnavn character varying(30),
    vejkode character varying(4),
    adresse character varying(80),
    matrikel character varying(80),
    vejkodenavn character varying(40),
    faktor integer,
    CONSTRAINT skilte_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS sidx_skilte_geom
    ON skilteplan.skilte USING gist
    (geom);

DROP TABLE IF EXISTS skilteplan.skiltetyper;

CREATE TABLE IF NOT EXISTS skilteplan.skiltetyper
(
    id serial,
    skiltenavn character varying(10),
    skiltebeskrivelse character varying(50),
    niveau integer,
    bredde double precision,
    hojde double precision,
    CONSTRAINT skiltetyper_pkey PRIMARY KEY (id)
);

DROP TABLE IF EXISTS skilteplan.skilteplan;

CREATE TABLE IF NOT EXISTS skilteplan.skilteplan
(
    planid integer NOT NULL,
    navn character varying(50),
    beskrivelse text,
    startdato date,
    slutdato date,
    kontaktorganisation character varying(100),
    kontaktperson character varying(80),
    kontakttelefon character varying(20),
    kontaktmail character varying(100),
    CONSTRAINT skilteplan_pkey PRIMARY KEY (planid)
);
