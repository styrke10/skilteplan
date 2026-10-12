# QGIS-plugin 'Skilteplan'

Skilteplaner udarbejdes ofte i forbindelse med midlertidige trafikomlægninger i forbindelse med f.eks. vejarbejder, ledningsarbejder, kortvarige arrangementer o.lign.

Plugin'et 'Skilteplan' gør QGIS velegnet til at udarbejde skilteplaner: Skilte placeres på kortet, roteres automatisk efter en vejmidte eller vejkant og forskydes fra den med et valgt
offset. Skilte kan have én eller to sider, og hver side består af en hovedtavle og op til 2 undertavler.

Hvert skilt hører til en navngiven skilteplan med periode og kontaktoplysninger, og planerne kan printes som atlas med én side pr. plan. 

Version 1.0 er en gennemgribende omskrivning. De væsentligste ændringer for dig som bruger:

•       **Frit valg af datakilde.** Plugin'et opretter tabellerne i enten GeoPackage eller PostGIS. Du placerer dem selv, hvor de skal ligge, og henter lagene ind i projektet.

•       **Ét skiltelag.** Manuelt og automatisk roterede skilte ligger nu i samme lag og styres af feltet manuelrotation. 

•       **Eget faneblad til skilteplaner.** Planer oprettes og redigeres i plugin'et i stedet for direkte i attributtabellen.

•       **Atlas og printlayout** oprettes automatisk, når projektet forberedes.

•       **Skiltebiblioteket fylder sig selv** ud fra SVG-filerne i skiltegrafikmappen.

•       **Projektet kan deles.** Opsætningen gemmes som projektvariabler, så en kollega kan åbne projektet og arbejde videre uden at sætte noget op.

En (simpel) skilteplan kan f.eks. se således ud:
<img width="624" height="500" alt="image" src="https://github.com/user-attachments/assets/8cb4d6f5-583d-407b-b4ec-550d7f931f2a" />
