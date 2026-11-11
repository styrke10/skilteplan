# -*- coding: utf-8 -*-
"""
Kernen i Skilteplan: skemadefinition, oprettelse af datakilder,
validering af lag samt atlaslag og printlayout.

skilteplan_skema er eneste kilde til feltdefinitionerne. Skal et felt
tilfoejes eller aendres, sker det i SKEMA og ingen andre steder - SQL,
GeoPackage, PostGIS og validering udledes derfra.
"""