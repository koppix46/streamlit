import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
DB_NAME = "roadbook.sqlite"
USER_ID = 2

st.set_page_config(page_title="RoadBook Training", layout="wide")

# --- HILFSFUNKTIONEN FÜR ZEIT-UMRECHNUNG ---
def minutes_to_hm(m):
    """Wandelt Minuten (int) in 'hh:mm' um."""
    try:
        m = int(m)
        return f"{m//60:02d}:{m%60:02d}"
    except:
        return "00:00"

def hm_to_minutes(s):
    """Wandelt 'hh:mm' in Minuten (int) um."""
    try:
        h, m = map(int, s.split(':'))
        return h * 60 + m
    except:
        return 0

# --- CSS FÜR ULTRA-KOMPAKTE DARSTELLUNG & ICONS ---
st.markdown("""
<style>
    .training-grid {
        display: grid;
        gap: 10px;
        align-items: center;
        padding: 8px 12px;
        border-bottom: 1px solid #eee;
        /* Feste Breite für Icons am Anfang (65px) */
        grid-template-columns: 65px 1.2fr 1fr 1.2fr 1.2fr 0.8fr 0.8fr 1.5fr 0.6fr;
    }

    .grid-header {
        font-weight: bold;
        background-color: #f8f9fb;
        border-bottom: 2px solid #4f8bf9;
        position: sticky;
        top: 0;
        z-index: 99;
    }

    /* Responsive Haltepunkte */
    @media (max-width: 1100px) {
        .training-grid { grid-template-columns: 65px 1.2fr 1fr 1.2fr 1.2fr !important; }
        .hide-tablet { display: none !important; }
    }

    @media (max-width: 700px) {
        .training-grid { grid-template-columns: 65px 1fr 1fr 1fr !important; }
        .hide-mobile { display: none !important; }
    }

    .cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }

    /* Icon-Links (Fritz!Box Style) */
    .icon-link {
        text-decoration: none !important;
        font-size: 18px;
        margin-right: 8px;
        filter: grayscale(100%);
        transition: filter 0.2s;
    }
    .icon-link:hover { filter: grayscale(0%); background-color: #f0f2f6; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- DATENBANK LOGIK ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def load_data(search=""):
    conn = get_connection()
    query = "SELECT rowid AS id, * FROM t_activities WHERE userid = ?"
    params = [USER_ID]
    if search:
        query += " AND (device LIKE ? OR cityfrom LIKE ? OR details LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    df = pd.read_sql_query(query + " ORDER BY date DESC LIMIT 100", conn, params=params)
    conn.close()
    return df

# --- BEARBEITEN / NEU DIALOG ---
@st.dialog("Eintrag bearbeiten")
def activity_dialog(row_id=None):
    is_new = row_id is None
    
    if not is_new:
        conn = get_connection()
        row = pd.read_sql_query("SELECT rowid AS id, * FROM t_activities WHERE rowid = ?", conn, params=[row_id]).iloc[0]
        conn.close()
    else:
        # Standardwerte für neuen Eintrag
        row = {
            'device': 'Cube', 'date': str(datetime.now().date()), 
            'cityfrom': 'Herzogenaurach', 'cityto': '', 'distance': 0, 
            'time': 60, 'details': '', 'vmax': 0, 'weight': 84.0
        }

    with st.form("edit_form", clear_on_submit=True):
        st.subheader("Details" if not is_new else "Neuer Eintrag")
        
        # Fokus-Safe: Sportgerät zuerst verhindert das Aufpoppen des Kalenders
        devs = ["Cube", "2 Danger", "Cannondale", "Adidas green", "Adidas black"]
        d_idx = devs.index(row['device']) if row['device'] in devs else 0
        new_device = st.selectbox("Sportgerät", devs, index=d_idx)
        
        c1, c2 = st.columns(2)
        with c1:
            new_date = st.date_input("Datum", value=datetime.strptime(row['date'], '%Y-%m-%d').date())
            new_from = st.text_input("Start (Von)", value=row['cityfrom'])
            new_to = st.text_input("Ziel (Nach)", value=row['cityto'])
        with c2:
            new_dist = st.number_input("Distanz (km)", value=float(row['distance'])/1000.0, step=0.1)
            new_time_str = st.text_input("Dauer (hh:mm)", value=minutes_to_hm(row['time']))
            new_vmax = st.number_input("vmax (max. km/h)", value=int(row['vmax']))
            
        new_details = st.text_area("Details", value=row['details'] or "")
        new_weight = st.number_input("Gewicht (kg)", value=float(row['weight'] or 84.0), step=0.1)

        st.divider()
        cols = st.columns(2)
        if cols[0].form_submit_button("💾 Speichern", type="primary", use_container_width=True):
            m_total = hm_to_minutes(new_time_str)
            conn = get_connection()
            if is_new:
                conn.execute("""
                    INSERT INTO t_activities (device, date, cityfrom, cityto, distance, time, details, vmax, weight, userid)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, USER_ID))
            else:
                conn.execute("""
                    UPDATE t_activities SET device=?, date=?, cityfrom=?, cityto=?, distance=?, time=?, details=?, vmax=?, weight=? 
                    WHERE rowid=?
                """, (new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, row_id))
            conn.commit(); conn.close()
            st.query_params.clear()
            st.rerun()
            
        if cols[1].form_submit_button("❌ Abbrechen", use_container_width=True):
            st.query_params.clear()
            st.rerun()

# --- HAUPTPROGRAMM ---
params = st.query_params
if "edit_id" in params:
    activity_dialog(params["edit_id"])
if "del_id" in params:
    conn = get_connection()
    conn.execute("DELETE FROM t_activities WHERE rowid = ?", (params["del_id"],))
    conn.commit(); conn.close()
    st.query_params.clear()
    st.rerun()

st.title("RoadBook Training")

# Top Bar
t1, t2 = st.columns([4, 1])
search_term = t1.text_input("Suche", placeholder="Nach Gerät oder Ort suchen...", label_visibility="collapsed")
if t2.button("➕ Neu", type="primary", use_container_width=True):
    activity_dialog()

data = load_data(search_term)

if not data.empty:
    # Tabellen Header
    st.markdown("""
        <div class="training-grid grid-header">
            <div class="cell">Aktion</div>
            <div class="cell">Datum</div>
            <div class="cell">Sport</div>
            <div class="cell">Start</div>
            <div class="cell hide-mobile">Ziel</div>
            <div class="cell hide-tablet">KM</div>
            <div class="cell hide-tablet">Zeit</div>
            <div class="cell hide-tablet">Details</div>
            <div class="cell hide-tablet">Vmax</div>
        </div>
    """, unsafe_allow_html=True)

    # Daten Zeilen
    for _, row in data.iterrows():
        st.markdown(f"""
            <div class="training-grid">
                <div>
                    <a href="?edit_id={row['id']}" target="_self" class="icon-link" title="Bearbeiten">📝</a>
                    <a href="?del_id={row['id']}" target="_self" class="icon-link" title="Löschen">🗑️</a>
                </div>
                <div class="cell">{row['date'].replace('-', '.')}</div>
                <div class="cell">{row['device']}</div>
                <div class="cell">{row['cityfrom']}</div>
                <div class="cell hide-mobile">{row['cityto']}</div>
                <div class="cell hide-tablet">{row['distance']/1000:.1f}</div>
                <div class="cell hide-tablet">{minutes_to_hm(row['time'])}</div>
                <div class="cell hide-tablet">{row['details'] or ''}</div>
                <div class="cell hide-tablet">{row['vmax']}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("Keine Daten vorhanden.")