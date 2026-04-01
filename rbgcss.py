import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
DB_NAME = "roadbook.sqlite"
USER_ID = 2

st.set_page_config(page_title="RoadBook Trainingstagebuch", layout="wide")

# --- DAS FINALE CSS (KEIN VERSATZ, KEIN UMBRUCH) ---
st.markdown("""
<style>
    /* 1. Definition der Spaltenbreiten für alle Ansichten */
    /* Wir nutzen CSS Variablen für absolute Konsistenz zwischen Header und Zeilen */
    :root {
        --grid-desktop: 1.2fr 1fr 1.5fr 1.5fr 0.8fr 0.8fr 1.5fr 0.6fr 80px;
        --grid-tablet: 1.5fr 1.2fr 2fr 80px;
        --grid-mobile: 1.5fr 1.2fr 80px;
    }

    .unified-grid {
        display: grid;
        grid-template-columns: var(--grid-desktop);
        gap: 10px;
        align-items: center;
        width: 100%;
    }

    @media (max-width: 1000px) {
        .hide-tablet { display: none !important; }
        .unified-grid { grid-template-columns: var(--grid-tablet); }
    }

    @media (max-width: 650px) {
        .hide-mobile { display: none !important; }
        .unified-grid { grid-template-columns: var(--grid-mobile); }
    }

    /* 2. Button-Umbruch verhindern (Der "Mobile-Retter") */
    /* Dieser Selektor zwingt Streamlit-Spalten innerhalb der Aktionsspalte zum Nebeneinander */
    [data-testid="column"]:last-child div[data-testid="stVerticalBlock"] {
        flex-direction: row !important;
        display: flex !important;
        gap: 5px !important;
        justify-content: flex-end;
    }

    /* 3. Design-Feinschliff */
    .table-header {
        font-weight: bold;
        border-bottom: 2px solid #4f8bf9;
        padding-bottom: 10px;
        margin-bottom: 10px;
        color: #444;
    }

    .data-row {
        padding: 10px 0;
        border-bottom: 1px solid #eee;
    }

    .data-cell {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* Buttons schmaler machen */
    .stButton button {
        width: 36px !important;
        height: 36px !important;
        padding: 0 !important;
        line-height: 1 !important;
    }

    /* Modal Fixes */
    [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-start; }
    .stTextInput, .stSelectbox, .stDateInput, .stNumberInput, .stTextArea { margin-bottom: 0px !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS t_activities (
            device TEXT, userid NUMERIC, cityfrom TEXT, cityto TEXT, 
            date DATETIME, distance REAL, time INTEGER, 
            details TEXT, vmax INTEGER, weight REAL)
    """)
    conn.close()

def load_data(search_term=""):
    conn = get_connection()
    query = "SELECT rowid AS id, * FROM t_activities WHERE userid = ?"
    params = [USER_ID]
    if search_term:
        query += " AND (device LIKE ? OR cityfrom LIKE ? OR cityto LIKE ? OR details LIKE ? OR date LIKE ?)"
        s = f"%{search_term}%"
        params.extend([s, s, s, s, s])
    query += " ORDER BY date DESC LIMIT 100"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def minutes_to_hm(minutes):
    return f"{int(minutes//60):02d}:{int(minutes%60):02d}"

def hm_to_minutes(hm_string):
    try:
        if ":" in hm_string:
            h, m = map(int, hm_string.split(':'))
            return h * 60 + m
        return int(hm_string)
    except: return 0

# --- MODAL ---
@st.dialog("Datensatz bearbeiten")
def show_edit_modal(activity=None):
    is_new = activity is None
    suffix = f": {activity['id']}" if not is_new else ""
    st.write(f"### bearbeite Datensatz{suffix}")

    with st.form("modal_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            d_str = activity['date'] if not is_new else str(datetime.now().date())
            date = st.date_input("Datum *", value=datetime.strptime(d_str, '%Y-%m-%d').date())
            devs = ["Cube", "2 Danger", "Cannondale", "Adidas green", "Adidas black"]
            d_idx = devs.index(activity['device']) if not is_new and activity['device'] in devs else 0
            device = st.selectbox("Sportgerät *", devs, index=d_idx)
            cityfrom = st.text_input("Start *", value=activity['cityfrom'] if not is_new else "Herzogenaurach")
            cityto = st.text_input("Ziel *", value=activity['cityto'] if not is_new else "Herzogenaurach")
        with c2:
            dist_val = float(activity['distance'])/1000.0 if not is_new else 0.0
            distance = st.number_input("Entfernung [km] *", value=dist_val, step=0.1, format="%.2f")
            dur_val = minutes_to_hm(activity['time']) if not is_new else "01:00"
            duration = st.text_input("Dauer (hh:mm) *", value=dur_val)
            weight = st.number_input("Gewicht [kg]", value=float(activity['weight']) if not is_new else 84.0, format="%.2f")
            vmax = st.number_input("vmax [km/h]", value=int(activity['vmax']) if not is_new else 0)
        
        details = st.text_area("Details", value=activity['details'] if not is_new else "", placeholder="Eingabe der Details")
        st.divider()
        b1, b2 = st.columns(2)
        if b1.form_submit_button("Speichern", type="primary", use_container_width=True):
            conn = get_connection()
            d_m = hm_to_minutes(duration)
            if is_new:
                conn.execute("INSERT INTO t_activities VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (device, USER_ID, cityfrom, cityto, str(date), distance*1000, d_m, details, vmax, weight))
            else:
                conn.execute("UPDATE t_activities SET device=?, cityfrom=?, cityto=?, date=?, distance=?, time=?, details=?, vmax=?, weight=? WHERE rowid=?",
                    (device, cityfrom, cityto, str(date), distance*1000, d_m, details, vmax, weight, activity['id']))
            conn.commit()
            conn.close()
            st.rerun()
        if b2.form_submit_button("zurück", use_container_width=True):
            st.rerun()

# --- MAIN ---
init_db()
st.title("Hans-Jürgen's Tracking Tool")
st.subheader("RoadBook Trainingstagebuch")

top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    search_query = st.text_input("", placeholder="Suchen...", label_visibility="collapsed")
with top_c2:
    if st.button("neuer Datensatz", type="primary", use_container_width=True):
        show_edit_modal()

data = load_data(search_query)

if not data.empty:
    # Header OHNE "Aktion" Text
    st.markdown(f"""
    <div class="unified-grid table-header">
        <div>Datum</div>
        <div>Sport</div>
        <div>Start</div>
        <div class="hide-mobile">Ziel</div>
        <div class="hide-tablet">Distanz</div>
        <div class="hide-tablet">Dauer</div>
        <div class="hide-tablet">Details</div>
        <div class="hide-tablet">vmax</div>
        <div></div> 
    </div>
    """, unsafe_allow_html=True)

    for _, row in data.iterrows():
        date_fmt = row['date'].replace('-', '.')
        dist_fmt = f"{row['distance']/1000:.1f} km"
        dur_fmt = minutes_to_hm(row['time'])
        det_fmt = (row["details"][:20] + "...") if row["details"] and len(row["details"]) > 20 else (row["details"] or "")
        
        # Wir nutzen einen Container pro Zeile
        row_container = st.container()
        col_data, col_btns = row_container.columns([0.92, 0.08])
        
        with col_data:
            st.markdown(f"""
            <div class="unified-grid data-row">
                <div class="data-cell">{date_fmt}</div>
                <div class="data-cell">{row['device']}</div>
                <div class="data-cell">{row['cityfrom']}</div>
                <div class="data-cell hide-mobile">{row['cityto']}</div>
                <div class="data-cell hide-tablet">{dist_fmt}</div>
                <div class="data-cell hide-tablet">{dur_fmt}</div>
                <div class="data-cell hide-tablet">{det_fmt}</div>
                <div class="data-cell hide-tablet">{row['vmax']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_btns:
            # Die Buttons werden durch das CSS oben gezwungen, nebeneinander zu stehen
            if st.button("📝", key=f"e_{row['id']}"):
                show_edit_modal(row)
            if st.button("🗑️", key=f"d_{row['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM t_activities WHERE rowid = ?", (row['id'],))
                conn.commit()
                conn.close()
                st.rerun()
else:
    st.info("Keine Datensätze gefunden.")