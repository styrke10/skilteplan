CREATE SCHEMA IF NOT EXISTS skilteplan;

DROP TABLE IF EXISTS skilteplan.skilte;

CREATE TABLE IF NOT EXISTS skilteplan.skilte
(
    id serial,
    geom geometry(Point,25832),
    planid integer,
    rotation double precision,
    retning character varying(10) COLLATE pg_catalog."default",
    "offset" double precision,
    dobbeltsidet boolean,
    type_forside character varying(10) COLLATE pg_catalog."default",
    utype_forside1 character varying(10) COLLATE pg_catalog."default",
    utype_forside2 character varying(10) COLLATE pg_catalog."default",
    type_bagside character varying(10) COLLATE pg_catalog."default",
    utype_bagside1 character varying(10) COLLATE pg_catalog."default",
    utype_bagside2 character varying(10) COLLATE pg_catalog."default",
    manuelrotation boolean,
    vejnavn character varying(30) COLLATE pg_catalog."default",
    vejkode character varying(4) COLLATE pg_catalog."default",
    adresse character varying(80) COLLATE pg_catalog."default",
    faktor integer,
    CONSTRAINT skilte_pkey PRIMARY KEY (id)
)

CREATE INDEX IF NOT EXISTS sidx_skilte_geom
    ON skilteplan.skilte USING gist
    (geom);
	
DROP TABLE IF EXISTS skilteplan.skilteplan;

CREATE TABLE IF NOT EXISTS skilteplan.skilteplan
(
    id serial,
    navn character varying(50) COLLATE pg_catalog."default",
    beskrivelse character varying(200) COLLATE pg_catalog."default",
    startdato date,
    slutdato date,
    CONSTRAINT skilteplan_pkey PRIMARY KEY (id)
)

DROP TABLE IF EXISTS skilteplan.skiltetyper;

CREATE TABLE IF NOT EXISTS skilteplan.skiltetyper
(
    id serial,
    skiltenavn character varying(10) COLLATE pg_catalog."default",
    skiltebeskrivelse character varying(50) COLLATE pg_catalog."default",
    niveau integer,
    bredde double precision,
    hojde double precision,
    CONSTRAINT skiltetyper_pkey PRIMARY KEY (id)
)
