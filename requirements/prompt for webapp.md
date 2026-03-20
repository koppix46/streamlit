# Erstelle für eine SQLITE3 Datenabnke eine Streamlit App_
- datenbankname: roadbook.sqlite 
- datenabankformat sqlite3

## Tabelle mit den Aktivitäten der Nutzer
CREATE TABLE 't_activities' ('device' NUMERIC NOT NULL,'userid' NUMERIC NOT NULL,'cityfrom' NUMERIC NOT NULL,'cityto' NUMERIC NOT NULL, 'date' DATETIME NOT NULL, 'distance' REAL NOT NULL,'time' INTEGER NOT NULL, 'details' TEXT, 'vmax' INTEGER, 'weight' REAL);

## Filter auf Datensätze
bitte nur für Datensätze mit userid = 1 umsetzen.

## Text to Requirements
Bitte parse die beiden Bilder im Arbeitsverzeichnis, denn sie enhalten eine Web Applikation, die mit PHP realisiet worden ist
erstelle die Streamlit App so wie auf dem Screenshot angezeigt:
- datei datagrid.png im Verzeichnis requirements
- datei form for each data record.png im Verzeichnis requirements

## weitere Rahmenbedingungen:
- beachte dass die Datenbankverbindung immer geschlossen wird, wenn sie nicht mehr benötigt wird.
- beachte dass die App so gestaltet ist, dass sie auch auf einem Smartphone gut bedienbar ist.
- beachte dass die App so gestaltet ist, dass sie auch auf einem Desktop gut bedienbar ist.
- beachte dass die App so gestaltet ist, dass sie auch auf einem Tablet gut bedienbar ist.
- beachte dass pro Datensatz ein Button zum löschen des Datensatzes vorhanden sein soll.
- beachte dass pro Datensatz ein Button zum bearbeiten des Datensatzes vorhanden sein soll.

## Name der App: rb.py

## Optionaler Feinschliff
- Datagrid echte Tabelle + Sortierung/Filter (Streamlit st.dataframe + Actions)
- h:m Umrechnung von Minute <-> Datensatz-Eingabe (optional separate UI)
- Smartphone/Tablet-optimierte Breakpoints durch st.columns-Logik (bereits responsive via Streamlit)
- zurückgestellt: Einträge direkt in Zeile editieren statt Expander (wenn exakt wie Screenshot gewünscht)