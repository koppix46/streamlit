import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from datetime import datetime
from time import perf_counter

# --- KONFIGURATION ---
DB_NAME = "roadbook.sqlite"
USER_ID = 2

st.set_page_config(page_title="RoadBook Trainingstagebuch", layout="wide")

# --- DATENBANK FUNKTIONEN ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS t_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT NOT NULL,
            userid NUMERIC NOT NULL,
            cityfrom TEXT NOT NULL,
            cityto TEXT NOT NULL,
            date DATETIME NOT NULL,
            distance REAL NOT NULL,
            time INTEGER NOT NULL,
            details TEXT,
            vmax INTEGER,
            weight REAL
        )
    """)
    conn.close()

def load_data(filter_text: str = "", max_rows: int = 100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(t_activities)")
    cols = [c[1] for c in cur.fetchall()]

    want_id = 'id' in cols
    base_sql = "SELECT {} FROM t_activities WHERE userid = ?"
    if want_id:
        select_fields = "*"
    else:
        select_fields = "rowid AS id, *"

    if filter_text:
        like_pattern = f"%{filter_text}%"
        base_sql += " AND (device LIKE ? OR cityfrom LIKE ? OR cityto LIKE ? OR details LIKE ? OR date LIKE ?)"
        params = (USER_ID, like_pattern, like_pattern, like_pattern, like_pattern, like_pattern)
    else:
        params = (USER_ID,)

    query = base_sql + " ORDER BY date DESC LIMIT ?"
    params = params + (max_rows,)

    df = pd.read_sql_query(query.format(select_fields), conn, params=params)
    conn.close()

    if 'id' not in df.columns and 'rowid' in df.columns:
        df.rename(columns={'rowid': 'id'}, inplace=True)

    return df

# --- HELPER: MINUTEN <-> HH:mm ---
def minutes_to_hm(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def hm_to_minutes(hm_string):
    try:
        h, m = map(int, hm_string.split(':'))
        return h * 60 + m
    except:
        return 0

# --- UI LOGIK ---
init_db()

st.title("Hans-Jürgen's Tracking Tool")
st.subheader("RoadBook Trainingstagebuch")

# Bildschirmbreite feststellen (responsive modus)
if 'screen_width' not in st.session_state:
    st.session_state.screen_width = 1400  # Standardwert für Desktop

if 'screen_mode' not in st.session_state:
    st.session_state.screen_mode = 'Desktop'

# Steuerleiste (Buttons) für Gerätemodus und Messwerte
if 'screen_mode' not in st.session_state:
    st.session_state.screen_mode = 'Desktop'
if 'screen_width' not in st.session_state:
    st.session_state.screen_width = 1400

cols = st.columns([1,1,1,2])
if cols[0].button("Desktop"):
    st.session_state.screen_mode = 'Desktop'
    st.session_state.screen_width = 1400
if cols[1].button("Tablet"):
    st.session_state.screen_mode = 'Tablet'
    st.session_state.screen_width = 1200
if cols[2].button("Smartphone"):
    st.session_state.screen_mode = 'Smartphone'
    st.session_state.screen_width = 900
if cols[3].button("Neu laden"):
    st.experimental_rerun()

st.markdown(
    f"**Modus:** {st.session_state.screen_mode} | "
    f"**Breite:** {st.session_state.screen_width}px"
)


# State für Editor-Modal (Simuliert)
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

# --- FORMULAR (NEU / BEARBEITEN) ---
with st.expander("➕ Neuer Datensatz / Bearbeiten", expanded=st.session_state.editing_id is not None):
    df = load_data()
    edit_data = df[df['id'] == st.session_state.editing_id].iloc[0] if st.session_state.editing_id else None
    
    with st.form("activity_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            date_val = datetime.strptime(edit_data['date'], '%Y-%m-%d').date() if edit_data is not None else datetime.now().date()
            date = st.date_input("Datum *", value=date_val)

            device_options = ["Cube", "2 Danger", "Cannondale"]
            if edit_data is None:
                device_index = 0
            else:
                try:
                    device_index = device_options.index(edit_data['device'])
                except ValueError:
                    device_index = 0

            device = st.selectbox("Sportgerät *", device_options, index=device_index)
            cityfrom = st.text_input("Start *", value=edit_data['cityfrom'] if edit_data is not None else "Herzogenaurach")
            cityto = st.text_input("Ziel *", value=edit_data['cityto'] if edit_data is not None else "Herzogenaurach")
        
        with col2:
            distance_km = float(edit_data['distance']) / 1000.0 if edit_data is not None else 0.0
            distance = st.number_input("Entfernung [km] *", value=distance_km, step=0.1)
            duration_str = st.text_input("Dauer [hh:mm] *", value=minutes_to_hm(edit_data['time']) if edit_data is not None else "00:00")
            weight = st.number_input("Gewicht [kg]", value=float(edit_data['weight']) if edit_data is not None else 84.0, step=0.1)
            vmax = st.number_input("vmax [km/h]", value=int(edit_data['vmax']) if edit_data is not None else 0, step=1)

        details = st.text_area("Details", value=edit_data['details'] if edit_data is not None else "")
        
        submitted = st.form_submit_button("Speichern")
        if submitted:
            conn = get_connection()
            duration_min = hm_to_minutes(duration_str)
            distance_m = distance * 1000.0
            
            if st.session_state.editing_id:
                conn.execute("""UPDATE t_activities SET device=?, cityfrom=?, cityto=?, date=?, distance=?, time=?, details=?, vmax=?, weight=? 
                             WHERE id=?""", (device, cityfrom, cityto, str(date), distance_m, duration_min, details, vmax, weight, st.session_state.editing_id))
                st.success("Datensatz aktualisiert!")
            else:
                conn.execute("""INSERT INTO t_activities (device, userid, cityfrom, cityto, date, distance, time, details, vmax, weight) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                             (device, USER_ID, cityfrom, cityto, str(date), distance_m, duration_min, details, vmax, weight))
                st.success("Datensatz gespeichert!")
            
            conn.commit()
            conn.close()
            st.session_state.editing_id = None
            st.rerun()

# --- DATAGRID ---
st.divider()
search_text = st.text_input("Datensätze suchen", value="", placeholder="z.B. Datum, Sportgerät, Start, Ziel, Details")
max_rows = st.slider("Maximale Zeilen (Limit)", min_value=10, max_value=500, value=100, step=10)

if search_text:
    st.info(f"Filter aktiv: '{search_text}' -> {max_rows} Zeilen max")

load_start = perf_counter()
data = load_data(filter_text=search_text.strip(), max_rows=max_rows)
load_time_ms = (perf_counter() - load_start) * 1000

st.write(f"Datensätze: {len(data)} | Ladezeit: {load_time_ms:.1f} ms")

if not data.empty:
    # Anzeige-Formatierung
    display_df = data.copy()
    display_df['Dauer [h:m]'] = display_df['time'].apply(minutes_to_hm)

    mode = st.session_state.get('screen_mode', 'Desktop')
    if mode == 'Desktop':
        visible_columns = ['date', 'device', 'cityfrom', 'cityto', 'distance', 'Dauer [h:m]', 'weight', 'vmax', 'actions']
        headers = ['Datum', 'Sport', 'Start', 'Ziel', 'Distanz', 'Dauer', 'Gewicht', 'vmax', 'Aktionen']
        col_widths = [2, 1.5, 2, 2, 1, 1, 1, 1, 1.5]
    elif mode == 'Tablet':
        visible_columns = ['date', 'device', 'cityfrom', 'cityto', 'actions']
        headers = ['Datum', 'Sport', 'Start', 'Ziel', 'Aktionen']
        col_widths = [2, 1.5, 2, 2, 1.5]
    else:  # Smartphone
        visible_columns = ['date', 'device', 'cityfrom', 'cityto']
        headers = ['Datum', 'Sport', 'Start', 'Ziel']
        col_widths = [2, 1.5, 2, 2]

    # Grid Header
    cols = st.columns(col_widths)
    for col, header in zip(cols, headers):
        col.write(f"**{header}**")

    for _, row in display_df.iterrows():
        row_cols = st.columns(col_widths)

        col_map = {
            'date': row_cols[0],
            'device': row_cols[1],
            'cityfrom': row_cols[2],
            'cityto': row_cols[3],
            'distance': row_cols[4] if len(row_cols) > 4 else None,
            'Dauer [h:m]': row_cols[5] if len(row_cols) > 5 else None,
            'weight': row_cols[6] if len(row_cols) > 6 else None,
            'vmax': row_cols[7] if len(row_cols) > 7 else None,
            'actions': row_cols[-1],
        }

        for col_key in visible_columns:
            if col_key == 'date':
                col_map[col_key].write(row['date'])
            elif col_key == 'device':
                col_map[col_key].write(row['device'])
            elif col_key == 'cityfrom':
                col_map[col_key].write(row['cityfrom'])
            elif col_key == 'cityto':
                col_map[col_key].write(row['cityto'])
            elif col_key == 'distance':
                dist_km = float(row['distance']) / 1000.0
                col_map[col_key].write(f"{dist_km:.1f} km")
            elif col_key == 'Dauer [h:m]':
                col_map[col_key].write(row['Dauer [h:m]'])
            elif col_key == 'weight':
                col_map[col_key].write(row['weight'])
            elif col_key == 'vmax':
                col_map[col_key].write(row['vmax'])
            elif col_key == 'actions':
                btn_edit, btn_del = col_map[col_key].columns(2)
                row_id = row['id'] if 'id' in row.index else row.get('rowid', None)

                if btn_edit.button("📝", key=f"edit_{row_id}"):
                    st.session_state.editing_id = row_id
                    st.rerun()

                if btn_del.button("🗑️", key=f"del_{row_id}"):
                    conn = get_connection()
                    if 'id' in display_df.columns:
                        conn.execute("DELETE FROM t_activities WHERE id = ?", (row_id,))
                    else:
                        conn.execute("DELETE FROM t_activities WHERE rowid = ?", (row_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
else:
    st.info("Noch keine Daten vorhanden.")