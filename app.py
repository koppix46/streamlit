import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import bcrypt
from libsql_client import create_client_sync
import extra_streamlit_components as stx

# --- 1. KONFIGURATION & DB-CLIENT ---
TURSO_URL = st.secrets["turso"]["url"]
TURSO_TOKEN = st.secrets["turso"]["token"]

st.set_page_config(page_title="RoadBook Training", layout="wide")

# Cookie Manager für den "Persistent Login"
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

def get_client():
    return create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

# --- 2. AUTHENTIFIZIERUNGS-LOGIK ---
def check_pw(password, hashed):
    if not hashed: return False
    return bcrypt.checkpw(password.encode(), hashed.encode())

def login_user(username, password):
    client = get_client()
    # Wir prüfen nickname und ob der User 'active' ist
    res = client.execute("SELECT userid, password_hash FROM t_users WHERE nickname = ? AND active = 1", [username])
    
    if res.rows:
        user_id, stored_hash = res.rows[0]
        if check_pw(password, stored_hash):
            # Login erfolgreich: Session Token für "Eingeloggt bleiben"
            new_token = str(uuid.uuid4())
            client.execute("UPDATE t_users SET session_token = ? WHERE userid = ?", [new_token, user_id])
            
            # Cookie für 30 Tage setzen
            cookie_manager.set("rb_auth_token", new_token, expires_at=datetime.now() + timedelta(days=30))
            st.session_state["userid"] = user_id
            client.close()
            return True
    client.close()
    return False

# --- 3. SESSION CHECK (AUTO-LOGIN) ---
if "userid" not in st.session_state:
    token = cookie_manager.get("rb_auth_token")
    if token:
        client = get_client()
        res = client.execute("SELECT userid FROM t_users WHERE session_token = ?", [token])
        client.close()
        if res.rows:
            st.session_state["userid"] = res.rows[0][0]

# --- 4. LOGIN MASK (Wird angezeigt, wenn nicht eingeloggt) ---
if "userid" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("<h3 style='text-align: center;'>Anmeldung an RoadBook</h3>", unsafe_allow_html=True)
        # Platzhalter für das User-Icon aus deinem Screenshot
        st.markdown("<div style='display: flex; justify-content: center;'><img src='https://cdn-icons-png.flaticon.com/512/149/149071.png' width='100'></div>", unsafe_allow_html=True)
        
        user_input = st.text_input("Benutzername", placeholder="Nickname")
        pass_input = st.text_input("Passwort", type="password", placeholder="Password")
        
        if st.button("Anmelden", use_container_width=True, type="primary"):
            if login_user(user_input, pass_input):
                st.rerun()
            else:
                st.error("Benutzername oder Passwort falsch.")
        
        st.caption("Kennwort zurücksetzen | neuer Benutzer?")
    st.stop()

# AB HIER: Benutzer ist erfolgreich eingeloggt
USER_ID = st.session_state["userid"]

# --- 5. DATEN LADEN (GEFILTERT AUF USER_ID) ---
def load_data(search=""):
    client = get_client()
    # Wichtig: Immer nach userid filtern!
    query = "SELECT rowid AS id, * FROM t_activities WHERE userid = ?"
    params = [USER_ID]
    
    if search:
        query += " AND (device LIKE ? OR cityfrom LIKE ? OR details LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    
    query += " ORDER BY date DESC LIMIT 100"
    result = client.execute(query, params)
    df = pd.DataFrame(result.rows, columns=result.columns)
    client.close()
    return df

# --- 6. HILFSFUNKTIONEN ---
def minutes_to_hm(m):
    try:
        m = int(m)
        return f"{m//60:02d}:{m%60:02d}"
    except: return "00:00"

def hm_to_minutes(s):
    try:
        h, m = map(int, s.split(':'))
        return h * 60 + m
    except: return 0

# --- 7. CSS ---
st.markdown("""
<style>
    .training-grid {
        display: grid; gap: 10px; align-items: center; padding: 8px 12px;
        border-bottom: 1px solid #eee;
        grid-template-columns: 65px 1.2fr 1fr 1.2fr 1.2fr 0.8fr 0.8fr 1.5fr 0.6fr;
    }
    .grid-header { font-weight: bold; background-color: #f8f9fb; border-bottom: 2px solid #4f8bf9; position: sticky; top: 0; z-index: 99; }
    @media (max-width: 1100px) { .training-grid { grid-template-columns: 65px 1.2fr 1fr 1.2fr 1.2fr !important; } .hide-tablet { display: none !important; } }
    @media (max-width: 700px) { .training-grid { grid-template-columns: 65px 1fr 1fr 1fr !important; } .hide-mobile { display: none !important; } }
    .cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
    .icon-link { text-decoration: none !important; font-size: 18px; margin-right: 8px; filter: grayscale(100%); transition: filter 0.2s; }
    .icon-link:hover { filter: grayscale(0%); background-color: #f0f2f6; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 8. DIALOGE ---
@st.dialog("Eintrag bearbeiten")
def activity_dialog(row_id=None):
    is_new = row_id is None
    client = get_client()
    
    if not is_new:
        res = client.execute("SELECT rowid AS id, * FROM t_activities WHERE rowid = ? AND userid = ?", [row_id, USER_ID])
        if not res.rows: 
            st.error("Nicht autorisiert.")
            return
        row = pd.DataFrame(res.rows, columns=res.columns).iloc[0]
    else:
        row = {
            'device': 'Cube', 'date': str(datetime.now().date()), 
            'cityfrom': 'Herzogenaurach', 'cityto': '', 'distance': 0, 
            'time': 60, 'details': '', 'vmax': 0, 'weight': 84.0
        }

    with st.form("edit_form", clear_on_submit=True):
        st.subheader("Details" if not is_new else "Neuer Eintrag")
        devs = ["Cube", "2 Danger", "Cannondale", "Adidas green", "Adidas black"]
        d_idx = devs.index(row['device']) if row['device'] in devs else 0
        new_device = st.selectbox("Sportgerät", devs, index=d_idx)
        
        c1, c2 = st.columns(2)
        with c1:
            new_date = st.date_input("Datum", value=datetime.strptime(str(row['date']), '%Y-%m-%d').date())
            new_from = st.text_input("Start", value=row['cityfrom'])
            new_to = st.text_input("Ziel", value=row['cityto'])
        with c2:
            new_dist = st.number_input("Distanz (km)", value=float(row['distance'])/1000.0, step=0.1)
            new_time_str = st.text_input("Dauer (hh:mm)", value=minutes_to_hm(row['time']))
            new_vmax = st.number_input("vmax (max. km/h)", value=int(row['vmax']))
            
        new_details = st.text_area("Details", value=row['details'] or "")
        new_weight = st.number_input("Gewicht (kg)", value=float(row['weight'] or 84.0), step=0.1)

        cols = st.columns(2)
        if cols[0].form_submit_button("💾 Speichern", type="primary", use_container_width=True):
            m_total = hm_to_minutes(new_time_str)
            if is_new:
                client.execute("INSERT INTO t_activities (device, date, cityfrom, cityto, distance, time, details, vmax, weight, userid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                               [new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, USER_ID])
            else:
                client.execute("UPDATE t_activities SET device=?, date=?, cityfrom=?, cityto=?, distance=?, time=?, details=?, vmax=?, weight=? WHERE rowid=? AND userid=?", 
                               [new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, row_id, USER_ID])
            client.close()
            st.rerun()
        if cols[1].form_submit_button("❌ Abbrechen", use_container_width=True):
            client.close()
            st.rerun()

# --- 9. HAUPTSEITE ---
# Logout & User Info in der Sidebar (Hamburger Menü)
with st.sidebar:
    st.title("User Profile")
    st.write(f"Angemeldet als: **User {USER_ID}**")
    if st.button("Abmelden", type="secondary"):
        client = get_client()
        client.execute("UPDATE t_users SET session_token = NULL WHERE userid = ?", [USER_ID])
        client.close()
        cookie_manager.delete("rb_auth_token")
        del st.session_state["userid"]
        st.rerun()

# Query Param Handling (Edit/Delete)
if "del_id" in st.query_params:
    client = get_client()
    client.execute("DELETE FROM t_activities WHERE rowid = ? AND userid = ?", [st.query_params["del_id"], USER_ID])
    client.close()
    st.query_params.clear()
    st.rerun()

if "edit_id" in st.query_params:
    activity_dialog(st.query_params["edit_id"])

st.title("RoadBook Training ☁️")

t1, t2 = st.columns([4, 1])
search_term = t1.text_input("Suche", placeholder="Nach Gerät oder Ort suchen...", label_visibility="collapsed")
if t2.button("➕ Neu", type="primary", use_container_width=True):
    activity_dialog()

data = load_data(search_term)

if not data.empty:
    st.markdown("""
        <div class="training-grid grid-header">
            <div class="cell">Aktion</div><div class="cell">Datum</div><div class="cell">Sport</div>
            <div class="cell">Start</div><div class="cell hide-mobile">Ziel</div><div class="cell hide-tablet">KM</div>
            <div class="cell hide-tablet">Zeit</div><div class="cell hide-tablet">Details</div><div class="cell hide-tablet">Vmax</div>
        </div>
    """, unsafe_allow_html=True)

    for _, row in data.iterrows():
        st.markdown(f"""
            <div class="training-grid">
                <div>
                    <a href="?edit_id={row['id']}" target="_self" class="icon-link">📝</a>
                    <a href="?del_id={row['id']}" target="_self" class="icon-link">🗑️</a>
                </div>
                <div class="cell">{str(row['date']).replace('-', '.')}</div>
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
    st.info("Keine Daten für diesen Benutzer gefunden.")