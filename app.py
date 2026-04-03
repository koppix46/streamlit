import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import bcrypt
from libsql_client import create_client_sync
import extra_streamlit_components as stx
import time

# --- 1. KONFIGURATION & DB-CLIENT ---
TURSO_URL = st.secrets["turso"]["url"]
TURSO_TOKEN = st.secrets["turso"]["token"]

st.set_page_config(
    page_title="RoadBook Training", 
    layout="wide", 
    initial_sidebar_state="collapsed" # <--- Diese Zeile sorgt für das Verstecken
)

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
    res = client.execute("SELECT userid, password_hash FROM t_users WHERE nickname = ? AND active = 1", [username])
    
    if res.rows:
        user_id, stored_hash = res.rows[0]
        if check_pw(password, stored_hash):
            new_token = str(uuid.uuid4())
            client.execute("UPDATE t_users SET session_token = ? WHERE userid = ?", [new_token, user_id])
            cookie_manager.set("rb_auth_token", new_token, expires_at=datetime.now() + timedelta(days=30))
            st.session_state["userid"] = user_id
            client.close()
            return True
    client.close()
    return False

# --- 3. SESSION CHECK (AUTO-LOGIN) ---
if "auth_checked" not in st.session_state:
    st.session_state["auth_checked"] = False

if "userid" not in st.session_state:
    token = cookie_manager.get("rb_auth_token")
    if token:
        client = get_client()
        res = client.execute("SELECT userid FROM t_users WHERE session_token = ?", [token])
        client.close()
        if res.rows:
            st.session_state["userid"] = res.rows[0][0]
            st.session_state["auth_checked"] = True
            st.rerun()
    elif not st.session_state["auth_checked"]:
        with st.spinner("Prüfe Autorisierung..."):
            st.session_state["auth_checked"] = True
            time.sleep(0.5) 
            st.rerun()

# Login Maske
if "userid" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>Anmeldung an RoadBook</h3>", unsafe_allow_html=True)
        st.markdown("<div style='display: flex; justify-content: center;'><img src='https://cdn-icons-png.flaticon.com/512/149/149071.png' width='100'></div>", unsafe_allow_html=True)
        user_input = st.text_input("Benutzername", placeholder="Nickname", autocomplete="username")
        pass_input = st.text_input("Passwort", type="password", placeholder="Password", autocomplete="current-password")
        if st.button("Anmelden", use_container_width=True, type="primary"):
            if login_user(user_input, pass_input):
                st.session_state["auth_checked"] = True
                st.rerun()
            else:
                st.error("Benutzername oder Passwort falsch.")
    st.stop()

USER_ID = st.session_state["userid"]

# --- 5. DATEN LADEN & STATISTIK ---
def load_data(search="", limit=400):
    client = get_client()
    query = "SELECT rowid AS id, * FROM t_activities WHERE userid = ?"
    params = [USER_ID]
    
    if search:
        terms = [t.strip() for t in search.split() if t.strip()]
        for term in terms:
            term_date = term.replace('.', '-')
            query += """ AND (LOWER(device) LIKE LOWER(?) OR LOWER(cityfrom) LIKE LOWER(?) OR LOWER(details) LIKE LOWER(?) OR date LIKE ?)"""
            s, sd = f"%{term}%", f"%{term_date}%"
            params.extend([s, s, s, sd])
    
    query += f" ORDER BY date DESC LIMIT {limit}"
    result = client.execute(query, params)
    df = pd.DataFrame(result.rows, columns=result.columns)
    client.close()
    return df

def get_default_values():
    client = get_client()
    # 1. Gewicht direkt vom User-Profil laden
    user_res = client.execute("SELECT weight FROM t_users WHERE userid = ?", [USER_ID])
    user_weight = float(user_res.rows[0][0] or 84.0) if user_res.rows else 84.0
    
    # 2. Letzte Aktivitäten für andere Defaults laden
    df_last = load_data(limit=100)
    client.close()
    
    if df_last.empty:
        return {
            'devs': ["Cube"], 
            'dist': 20.0, 
            'time': 60, 
            'vmax': 25, 
            'from': "Herzogenaurach", 
            'weight': user_weight # <--- User Profil Gewicht
        }
    
    return {
        'devs': sorted(df_last['device'].unique().tolist()),
        'dist': round(df_last['distance'].mean() / 1000.0, 1),
        'time': int(df_last['time'].mean()),
        'vmax': int(df_last['vmax'].mean()),
        'from': df_last['cityfrom'].iloc[0],
        'weight': user_weight # <--- User Profil Gewicht statt letztem Eintrag
    }

# --- 6. HILFSFUNKTIONEN ---
def minutes_to_hm(m):
    try:
        m = int(m)
        return f"{m//60:02d}:{m%60:02d}"
    except: return "00:00"

def hm_to_minutes(s):
    try:
        if ':' in s:
            h, m = map(int, s.split(':'))
            return h * 60 + m
        return int(s)
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
    .cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
    .icon-link { text-decoration: none !important; font-size: 18px; margin-right: 8px; filter: grayscale(100%); transition: filter 0.2s; }
    .icon-link:hover { filter: grayscale(0%); background-color: #f0f2f6; border-radius: 4px; }
    @media (max-width: 1100px) { .training-grid { grid-template-columns: 65px 1.2fr 1fr 1.2fr 1.2fr !important; } .hide-tablet { display: none !important; } }
    @media (max-width: 700px) { .training-grid { grid-template-columns: 65px 1fr 1fr 1fr !important; } .hide-mobile { display: none !important; } }
</style>
""", unsafe_allow_html=True)

# --- 8. DIALOGE ---
@st.dialog("Benutzerprofil bearbeiten")
def user_settings_dialog():
    client = get_client()
    # Alle benötigten Spalten abrufen
    user_res = client.execute(
        "SELECT nickname, weight, email, firstname, lastname FROM t_users WHERE userid = ?", 
        [USER_ID]
    )
    
    if user_res.rows:
        row = user_res.rows[0]
        curr_nick, curr_weight, curr_email, curr_first, curr_last = row
    else:
        st.error("Benutzer nicht gefunden.")
        client.close()
        return
    client.close()

    with st.form("user_edit_form", clear_on_submit=False):
        st.subheader("Persönliche Daten")
        
        # Erste Zeile: Vorname & Nachname
        col_name1, col_name2 = st.columns(2)
        new_first = col_name1.text_input("Vorname", value=curr_first or "")
        new_last = col_name2.text_input("Nachname", value=curr_last or "")
        
        # Zweite Zeile: Anzeigename & Email
        new_nick = st.text_input("Anzeigename (Nickname)", value=curr_nick or "")
        new_email = st.text_input("Email", value=curr_email or "")
        
        # Dritte Zeile: Gewicht
        new_weight = st.number_input("Standard-Gewicht (kg)", value=float(curr_weight or 80.0), step=0.1)
        
        st.divider()
        st.subheader("Sicherheit")
        new_pass = st.text_input("Neues Passwort", type="password", help="Leer lassen für kein Update")
        confirm_pass = st.text_input("Passwort wiederholen", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(2)
        
        if cols[0].form_submit_button("💾 Speichern", type="primary", use_container_width=True):
            if new_pass and new_pass != confirm_pass:
                st.error("Passwörter stimmen nicht überein!")
            elif not new_nick:
                st.error("Anzeigename darf nicht leer sein.")
            else:
                client = get_client()
                try:
                    if new_pass:
                        hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                        client.execute(
                            """UPDATE t_users SET 
                               nickname = ?, password_hash = ?, weight = ?, 
                               email = ?, firstname = ?, lastname = ? 
                               WHERE userid = ?""", 
                            [new_nick, hashed, new_weight, new_email, new_first, new_last, USER_ID]
                        )
                    else:
                        client.execute(
                            """UPDATE t_users SET 
                               nickname = ?, weight = ?, email = ?, 
                               firstname = ?, lastname = ? 
                               WHERE userid = ?""", 
                            [new_nick, new_weight, new_email, new_first, new_last, USER_ID]
                        )
                    client.close()
                    st.success("Profil erfolgreich aktualisiert!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
                    client.close()
                    
        if cols[1].form_submit_button("❌ Abbrechen", use_container_width=True):
            st.rerun()
            
@st.dialog("Eintrag bearbeiten")
def activity_dialog(row_id=None):
    is_new = row_id is None
    client = get_client()
    defaults = get_default_values()
    
    if not is_new:
        res = client.execute("SELECT rowid AS id, * FROM t_activities WHERE rowid = ? AND userid = ?", [row_id, USER_ID])
        if not res.rows: st.error("Fehler"); return
        row = pd.DataFrame(res.rows, columns=res.columns).iloc[0]
        current_devs = sorted(list(set(defaults['devs'] + [row['device']])))
    else:
        row = {'device': defaults['devs'][0], 'date': str(datetime.now().date()), 'cityfrom': defaults['from'], 'cityto': '', 'distance': defaults['dist'] * 1000, 'time': defaults['time'], 'details': '', 'vmax': defaults['vmax'], 'weight': defaults['weight']}
        current_devs = defaults['devs']

    with st.form("edit_form", clear_on_submit=True):
        st.subheader("Details" if not is_new else "Neuer Eintrag")
        d_idx = current_devs.index(row['device']) if row['device'] in current_devs else 0
        new_device = st.selectbox("Sportgerät", current_devs, index=d_idx)
        c1, c2 = st.columns(2)
        with c1:
            new_date = st.date_input("Datum", value=datetime.strptime(str(row['date']), '%Y-%m-%d').date())
            new_from = st.text_input("Start", value=row['cityfrom'])
            new_to = st.text_input("Ziel", value=row['cityto'])
        with c2:
            new_dist = st.number_input("Distanz (km)", value=float(row['distance'])/1000.0, step=0.1)
            new_time_str = st.text_input("Dauer (hh:mm)", value=minutes_to_hm(row['time']))
            new_vmax = st.number_input("vmax (km/h)", value=int(row['vmax']))
        new_details = st.text_area("Details", value=row['details'] or "")
        new_weight = st.number_input("Gewicht (kg)", value=float(row['weight'] or 84.0), step=0.1)

        cols = st.columns(2)
        if cols[0].form_submit_button("💾 Speichern", type="primary", use_container_width=True):
            m_total = hm_to_minutes(new_time_str)
            if is_new:
                client.execute("INSERT INTO t_activities (device, date, cityfrom, cityto, distance, time, details, vmax, weight, userid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, USER_ID])
            else:
                client.execute("UPDATE t_activities SET device=?, date=?, cityfrom=?, cityto=?, distance=?, time=?, details=?, vmax=?, weight=? WHERE rowid=? AND userid=?", [new_device, str(new_date), new_from, new_to, new_dist*1000, m_total, new_details, new_vmax, new_weight, row_id, USER_ID])
            client.close(); st.query_params.clear(); st.rerun()
        if cols[1].form_submit_button("❌ Abbrechen", use_container_width=True): client.close(); st.query_params.clear(); st.rerun()

# --- 9. HAUPTSEITE ---
with st.sidebar:
    st.title("RoadBook Menü")
    client = get_client()
    user_res = client.execute("SELECT nickname FROM t_users WHERE userid = ?", [USER_ID])
    display_name = user_res.rows[0][0] if user_res.rows else f"User {USER_ID}"
    client.close()
    st.info(f"Eingeloggt als: **{display_name}**")
    st.divider()
    if st.button("👤 Profil-Einstellungen", use_container_width=True): user_settings_dialog()
    if st.button("🚪 Abmelden", type="secondary", use_container_width=True):
        client = get_client(); client.execute("UPDATE t_users SET session_token = NULL WHERE userid = ?", [USER_ID]); client.close()
        cookie_manager.delete("rb_auth_token"); del st.session_state["userid"]; st.rerun()

st.title("RoadBook Training ☁️")
search_term = st.text_input("Suche", placeholder="Gerät, Ort, Datum (z.B. 2026.04)...", label_visibility="collapsed", key="search")
if search_term and ("edit_id" in st.query_params or "del_id" in st.query_params): st.query_params.clear(); st.rerun()

if "del_id" in st.query_params:
    client = get_client(); client.execute("DELETE FROM t_activities WHERE rowid = ? AND userid = ?", [st.query_params["del_id"], USER_ID]); client.close()
    st.query_params.clear(); st.rerun()
if "edit_id" in st.query_params: activity_dialog(st.query_params["edit_id"])

t1, t2 = st.columns([4, 1])
with t2:
    if st.button("➕ Neu", type="primary", use_container_width=True): st.query_params.clear(); activity_dialog()

data = load_data(search_term)

if not data.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Gesamt Distanz", f"{data['distance'].sum()/1000.0:.1f} km")
    c2.metric("Gesamt Zeit", minutes_to_hm(data['time'].sum()))
    c3.metric("Max Vmax", f"{data['vmax'].max()} km/h")

    st.markdown("""<div class="training-grid grid-header"><div class="cell">Aktion</div><div class="cell">Datum</div><div class="cell">Sport</div><div class="cell">Start</div><div class="cell hide-mobile">Ziel</div><div class="cell hide-tablet">KM</div><div class="cell hide-tablet">Zeit</div><div class="cell hide-tablet">Details</div><div class="cell hide-tablet">Vmax</div></div>""", unsafe_allow_html=True)
    for _, row in data.iterrows():
        st.markdown(f"""<div class="training-grid"><div><a href="?edit_id={row['id']}" target="_self" class="icon-link">📝</a><a href="?del_id={row['id']}" target="_self" class="icon-link">🗑️</a></div><div class="cell">{str(row['date']).replace('-', '.')}</div><div class="cell">{row['device']}</div><div class="cell">{row['cityfrom']}</div><div class="cell hide-mobile">{row['cityto']}</div><div class="cell hide-tablet">{row['distance']/1000:.1f}</div><div class="cell hide-tablet">{minutes_to_hm(row['time'])}</div><div class="cell hide-tablet">{row['details'] or ''}</div><div class="cell hide-tablet">{row['vmax']}</div></div>""", unsafe_allow_html=True)
else:
    st.info("Keine Daten gefunden.")