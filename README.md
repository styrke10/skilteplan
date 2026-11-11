# QGIS-plugin 'Skilteplan'

Skilteplaner udarbejdes ofte i forbindelse med midlertidige trafikomlægninger i forbindelse med f.eks. vejarbejder, ledningsarbejder, kortvarige arrangementer o.lign.

Plugin'et 'Skilteplan' gør QGIS velegnet til at udarbejde skilteplaner: Skilte placeres på kortet, roteres automatisk efter en vejmidte eller vejkant og forskydes fra den med et valgt offset. Skilte kan have én eller to sider, og hver side består af en hovedtavle og op til 2 undertavler.

Hvert skilt hører til en navngiven skilteplan med periode og kontaktoplysninger, og planerne kan printes som atlas med én side pr. plan. 

Version 1.1 er en gennemgribende omskrivning. De væsentligste ændringer for dig som bruger:

•       **Frit valg af datakilde.** Plugin'et opretter tabellerne i enten GeoPackage eller PostGIS. Du placerer dem selv, hvor de skal ligge, og henter lagene ind i projektet.

•       **Ét skiltelag.** Manuelt og automatisk roterede skilte ligger nu i samme lag og styres af feltet manuelrotation. 

•       **Eget faneblad til skilteplaner.** Planer oprettes og redigeres i plugin'et i stedet for direkte i attributtabellen.

•       **Atlas og printlayout** oprettes automatisk, når projektet forberedes.

•       **Skiltebiblioteket fylder sig selv** ud fra SVG-filerne i skiltegrafikmappen.

•       **Projektet kan deles.** Opsætningen gemmes som projektvariabler, så en kollega kan åbne projektet og arbejde videre uden at sætte noget op.

En (simpel) skilteplan kan f.eks. se således ud:

<img width="624" height="500" alt="image" src="https://github.com/user-attachments/assets/8cb4d6f5-583d-407b-b4ec-550d7f931f2a" />

---

## English

Traffic sign plans (*skilteplaner*) are often prepared for temporary traffic diversions, e.g. during road works, utility works, short-term events and the like.

The 'Skilteplan' plugin makes QGIS well suited for preparing traffic sign plans: signs are placed on the map, rotated automatically to follow a road centreline or road edge, and offset from it by a chosen distance. Signs can have one or two sides, and each side consists of a main sign and up to 2 supplementary plates.

Each sign belongs to a named sign plan with a period and contact details, and the plans can be printed as an atlas with one page per plan.

Version 1.1 is a complete rewrite. The most important changes for you as a user:

•       **Free choice of data source.** The plugin creates the tables in either GeoPackage or PostGIS. You decide where they are stored and load the layers into the project yourself.

•       **One sign layer.** Manually and automatically rotated signs are now stored in the same layer and controlled by the field manuelrotation.

•       **Dedicated tab for sign plans.** Plans are created and edited in the plugin instead of directly in the attribute table.

•       **Atlas and print layout** are created automatically when the project is prepared.

•       **The sign library populates itself** from the SVG files in the sign graphics folder.

•       **The project can be shared.** The setup is saved as project variables, so a colleague can open the project and continue working without having to set anything up.

A (simple) sign plan could, for example, look like the one shown above.
