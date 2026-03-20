# datenbankname: roadbook.sqlite 
# datenabankformat sqlite3

# tabelle mit den Aktivitäten der Nutzer
CREATE TABLE 't_activities' ('device' NUMERIC NOT NULL,'userid' NUMERIC NOT NULL,'cityfrom' NUMERIC NOT NULL,'cityto' NUMERIC NOT NULL, 'date' DATETIME NOT NULL, 'distance' REAL NOT NULL,'time' INTEGER NOT NULL, 'details' TEXT, 'vmax' INTEGER, 'weight' REAL);

# tabelle mit den Nutzern
CREATE TABLE 't_users' ('userid' INTEGER UNIQUE PRIMARY KEY AUTOINCREMENT NOT NULL, 'nickname' NUMERIC UNIQUE NOT NULL, 'token' NUMERIC UNIQUE NOT NULL, 'firstname' NUMERIC, 'lastname' NUMERIC, 'password' NUMERIC NOT NULL, 'city' NUMERIC NOT NULL, 'device' NUMERIC NOT NULL, 'weight' INTEGER, 'email' NUMERIC UNIQUE, 'active' BOOLEAN);

