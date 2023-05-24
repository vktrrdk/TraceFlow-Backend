[ ] Welche Lösungen gibt es?
[ ] Was kann NF tower? 
[ ] Gibt es andere Beispiele/Lösungen, woran kann man sich auch ein Beispiel nehmen?
[ ] Welche Frameworks kann man für die Lösungen nehmen? Vergleich! Vor- und Nachteile
 
### Implementation Erste Schritte - API Token

- [ ] Welche Frameworks? django zu groß? Flask (https://flask.palletsprojects.com/en/2.2.x/)?

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



aktuelle Probleme:

ModuleNotFoundError: No module named 'pydantic'  klappt außerhalb des containers
warum ?

check if mongo-db really is the best way to do it
validierung von users, runs und tokens und unique users and tokens

django statt flask...? 
vorhandene projekte auf github abchecken!


check this: https://github.com/tiangolo/full-stack-fastapi-postgresql

check the annotation stuff - why is python 3.9 runnning and not 3.11?
    https://fastapi.tiangolo.com/tutorial/query-params-str-validations/

alembic - migrationen in die db kriegen