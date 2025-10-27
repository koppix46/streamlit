import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Name der DatenbankdateiöÜÜüöö
DB_FILE = "roadbook.sqlite"

# Funktion zum Laden der Daten aus der Datenbank mit Caching
@st.cache_data
def load_data(db_file):
    """
    Stellt eine Verbindung zur SQLite-Datenbank her,
    führt die Abfrage aus und gibt das Ergebnis in einem Pandas DataFrame zurück.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # SQL-Abfrage für verschiedene Zeiträume
        query = """
                WITH metrics AS (
                    SELECT 
                        round(sum(CASE 
                            WHEN date(date) = date('now') 
                            THEN distance END) / 1000.0, 1) as today_distance,
                        round(sum(CASE 
                            WHEN strftime('%Y-%W', date) = strftime('%Y-%W', 'now') 
                            THEN distance END) / 1000.0, 1) as week_distance,
                        round(sum(CASE 
                            WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now') 
                            THEN distance END) / 1000.0, 1) as month_distance,
                        round(sum(CASE 
                            WHEN ((cast(strftime('%m', date) as integer) - 1) / 3) = 
                                 ((cast(strftime('%m', 'now') as integer) - 1) / 3)
                            AND strftime('%Y', date) = strftime('%Y', 'now')
                            THEN distance END) / 1000.0, 1) as quarter_distance,
                        round(sum(CASE 
                            WHEN strftime('%Y', date) = strftime('%Y', 'now') 
                            THEN distance END) / 1000.0, 1) as year_distance,
                        round(sum(distance) / 1000.0, 1) as total_distance
                    FROM t_activities 
                    WHERE userid = 1
                )
                SELECT 
                    COALESCE(today_distance, 0) as today_distance,
                    COALESCE(week_distance, 0) as week_distance,
                    COALESCE(month_distance, 0) as month_distance,
                    COALESCE(quarter_distance, 0) as quarter_distance,
                    COALESCE(year_distance, 0) as year_distance,
                    COALESCE(total_distance, 0) as total_distance
                FROM metrics;
                """
        df = pd.read_sql_query(query, conn)
        return df
    except sqlite3.Error as e:
        st.error(f"Fehler beim Verbinden mit der Datenbank oder Ausführen der Abfrage: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# Streamlit App-Titel
st.title("Roadbook: Aktivitäten")
st.header("Übersicht der Aktivitäten")

# Daten laden
df_activities = load_data(DB_FILE)

# Überprüfen, ob Daten vorhanden sind und anzeigen
if not df_activities.empty:
    # Aktuelle Zeitangaben für Überschriften
    current_date = datetime.now()
    current_quarter = ((current_date.month - 1) // 3) + 1

    # Layout mit 3 Spalten
    col1, col2, col3 = st.columns(3)
    
    # Erste Reihe
    with col1:
        st.metric(
            label="Heute",
            value=f"{df_activities['today_distance'].iloc[0]} km"
        )
    with col2:
        st.metric(
            label="Diese Woche",
            value=f"{df_activities['week_distance'].iloc[0]} km"
        )
    with col3:
        st.metric(
            label="Dieser Monat",
            value=f"{df_activities['month_distance'].iloc[0]} km"
        )
    
    # Zweite Reihe
    with col1:
        st.metric(
            label=f"{current_quarter}. Quartal {current_date.year}",
            value=f"{df_activities['quarter_distance'].iloc[0]} km"
        )
    with col2:
        st.metric(
            label=f"Jahr {current_date.year}",
            value=f"{df_activities['year_distance'].iloc[0]} km"
        )
    with col3:
        st.metric(
            label="Gesamt",
            value=f"{df_activities['total_distance'].iloc[0]} km"
        )
    
    # Detaillierte Datenansicht
    if st.checkbox("Details anzeigen"):
        st.dataframe(df_activities)
else:
    st.warning("Es konnten keine Daten geladen oder gefunden werden.")
