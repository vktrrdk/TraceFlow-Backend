
### Implementation Erste Schritte - API Token

- [ ] Welche Frameworks? FAST API   

API-Token - a la: testplatform.de/path/token=1123521354234 …  cmd: weblog http://testplatform.de/path/token=1123521354234
Token pro Nutzer oder pro Aufruf? Token nur für die Plattform, aber nicht für die lokale Ausführung
Token aus CloWM: Plattform soll Token für den Run generieren. ... --with—weblog http://testplatform.de/path/token=1123521354234
token pro nutzer - id für run wird von eigener Plattform generiert - damit ist es möglich mehrere Rund in einer Übersicht anzuzeigen

### Orga

- [ ] Daniels Projekt anschauen
- [ ] LaTex-Template anlegen

### Schriftlich
 - Was ist de.NBI?
 - Was ist das Toolkit ...
 - Was ist die Herausforderungen, was sind die Rahmenbedingungen und was ist das Ziel? 
 - Was ist das Projekt?
 - Welche Lösungen gibt es?
 - Was kann NF tower? 
 - Gibt es andere Beispiele/Lösungen, woran kann man sich auch ein Beispiel nehmen?
 - Welche Frameworks kann man für die Lösungen nehmen? Vergleich! Vor- und Nachteile
 - Was ist das Ziel der Implementation?

alembic und sql-alchemy verstehen

# Weitere Schritte

 - Token/User handling fertigstellen (Sqlalchemy) (es fehlen noch einige sachen)
 - get post usw anpassen !
 - vererbung betrachten (models) !
 - error handling !
 - Kontakt mit Goebel und Beckstette !
 - Vorschläge für Schnittstellen !
 - Anbindung von Nextflow traces !
 - Persistenz von traces !
 - UML Diagramme machen
 - Nochmal schauen wie die Config von nextflow angepasst werden kann, sodass man mehr metriken bekommt!
 - checken warum man meta objecte doppelt speichert/bekommt? selbes für trace?
 - check https://router.vuejs.org/guide/ und components
 - responses der api anpassen!