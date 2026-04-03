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
INVITE_CODE = "Training2026"  
ADMIN_NICKNAME = "koppix"     # Kleingeschrieben für den Vergleich

st.set_page_config(
    page_title="RoadBook Training", 
    layout="wide", 
    initial_sidebar_state="collapsed"
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
    res = client.execute("SELECT userid, password_hash, active FROM t_users WHERE nickname = ?", [username])
    
    if res.rows:
        user_id, stored_hash, is_active = res.rows[0]
        if is_active != 1:
            st.error("Account noch nicht freigeschaltet.")
            client.close()
            return False
        if check_pw(password, stored_hash):
            new_token = str(uuid.uuid4())
            client.execute("UPDATE t_users SET session_token = ? WHERE userid = ?", [new_token, user_id])
            cookie_manager.set("rb_auth_token", new_token, expires_at=datetime.now() + timedelta(days=30))
            st.session_state["userid"] = user_id
            client.close()
            return True
    client.close()
    st.error("Logindaten nicht korrekt.")
    return False

# --- 3. CSS (RESPONSIVE GRID) ---
st.markdown("""
<style>
    .training-grid {
        display: grid; gap: 10px; align-items: center; padding: 8px 12px;
        border-bottom: 1px solid #eee;
        grid-template-columns: 80px 1.2fr 1fr 1.2fr 1.2fr 0.8fr 0.8fr 1.5fr 0.6fr;
    }
    .grid-header { font-weight: bold; background-color: #f8f9fb; border-bottom: 2px solid #4f8bf9; }
    .cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
    .icon-link { text-decoration: none !important; font-size: 18px; margin-right: 10px; }
    
    @media (max-width: 1100px) { 
        .training-grid { grid-template-columns: 80px 1.2fr 1fr 1.2fr 1.2fr !important; } 
        .hide-tablet { display: none !important; } 
    }
    @media (max-width: 700px) { 
        .training-grid { grid-template-columns: 80px 1fr 1fr 1fr !important; } 
        .hide-mobile { display: none !important; } 
    }
</style>
""", unsafe_allow_html=True)

# --- 4. DIALOGE ---

@st.dialog("Administrator-Konsole", width="large")
def admin_dialog():
    client = get_client()
    st.subheader("Nutzerverwaltung & Sicherheit")
    tab1, tab2 = st.tabs(["⏳ Neue Freischaltungen", "🔑 Passwort-Reset"])
    
    with tab1:
        inactive = client.execute("SELECT userid, nickname, firstname, lastname, email FROM t_users WHERE active = 0")
        if not inactive.rows:
            st.info("Keine ausstehenden Registrierungen.")
        else:
            for u in inactive.rows:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{u[1]}** ({u[2]} {u[3]})  \n*{u[4]}*")
                    if c2.button("Aktivieren", key=f"adm_act_{u[0]}", use_container_width=True):
                        client.execute("UPDATE t_users SET active = 1 WHERE userid = ?", [u[0]])
                        st.success(f"{u[1]} freigeschaltet!"); time.sleep(1); st.rerun()
    
    with tab2:
        all_u = client.execute("SELECT userid, nickname FROM t_users WHERE active = 1")
        u_dict = {r[1]: r[0] for r in all_u.rows}
        target = st.selectbox("Benutzer wählen", options=list(u_dict.keys()), key="reset_user_sel")
        new_pw = st.text_input("Neues Kennwort vergeben", type="password", key="reset_pw_in")
        if st.button("Passwort jetzt überschreiben", type="primary", use_container_width=True):
            if new_pw:
                hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                client.execute("UPDATE t_users SET password_hash = ?, session_token = NULL WHERE userid = ?", [hashed, u_dict[target]])
                st.success(f"Passwort für {target} wurde geändert!"); time.sleep(1); st.rerun()
    client.close()
    if st.button("Schließen", use_container_width=True): st.rerun()

@st.dialog("Erfassung eines neuen Benutzers")
def registration_dialog():
    with st.form("reg_form", clear_on_submit=False):
        st.info("Hinweis: Ein Admin muss dich freischalten.")
        c1, c2 = st.columns(2)
        with c1:
            vname = st.text_input("Vorname *")
            nick = st.text_input("Nickname *")
            pass1 = st.text_input("Kennwort *", type="password")
            mail1 = st.text_input("Email *")
        with c2:
            nname = st.text_input("Nachname *")
            invite = st.text_input("Einladungscode *", type="password")
            pass2 = st.text_input("Kennwort wiederholen *", type="password")
            mail2 = st.text_input("Email wiederholen *")
        weight = st.number_input("Gewicht [kg]", value=80.0, step=0.1)

        if st.form_submit_button("Registrieren", type="primary", use_container_width=True):
            if not (vname and nname and nick and pass1 and mail1 and invite):
                st.error("Pflichtfelder fehlen!")
            elif invite != INVITE_CODE:
                st.error("Falscher Einladungscode.")
            elif pass1 != pass2 or mail1 != mail2:
                st.error("Passwörter ungleich.")
            else:
                client = get_client()
                check = client.execute("SELECT userid FROM t_users WHERE nickname = ?", [nick])
                if check.rows:
                    st.error("Nickname vergeben."); client.close()
                else:
                    hashed = bcrypt.hashpw(pass1.encode(), bcrypt.gensalt()).decode()
                    client.execute("INSERT INTO t_users (firstname, lastname, nickname, password_hash, email, weight, active) VALUES (?,?,?,?,?,?,0)", [vname, nname, nick, hashed, mail1, weight])
                    client.close(); st.success("Registriert!"); time.sleep(2); st.rerun()

@st.dialog("Benutzerprofil bearbeiten")
def user_settings_dialog():
    client = get_client()
    res = client.execute("SELECT nickname, weight, email, firstname, lastname FROM t_users WHERE userid = ?", [st.session_state["userid"]])
    curr = res.rows[0]; client.close()
    with st.form("user_edit_form"):
        col1, col2 = st.columns(2)
        new_first = col1.text_input("Vorname", value=curr[3] or "")
        new_last = col2.text_input("Nachname", value=curr[4] or "")
        new_nick = st.text_input("Nickname", value=curr[0] or "")
        new_email = st.text_input("Email", value=curr[2] or "")
        new_weight = st.number_input("Gewicht (kg)", value=float(curr[1] or 80.0), step=0.1)
        st.divider()
        new_pass = st.text_input("Neues Passwort", type="password")
        confirm_pass = st.text_input("Wiederholen", type="password")
        if st.form_submit_button("Speichern", type="primary"):
            client = get_client()
            if new_pass and new_pass == confirm_pass:
                hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                client.execute("UPDATE t_users SET nickname=?, weight=?, email=?, firstname=?, lastname=?, password_hash=? WHERE userid=?", [new_nick, new_weight, new_email, new_first, new_last, hashed, st.session_state["userid"]])
            else:
                client.execute("UPDATE t_users SET nickname=?, weight=?, email=?, firstname=?, lastname=? WHERE userid=?", [new_nick, new_weight, new_email, new_first, new_last, st.session_state["userid"]])
            client.close(); st.success("Profil aktualisiert!"); time.sleep(1); st.rerun()

# --- 5. SESSION & AUTO-LOGIN ---
if "auth_checked" not in st.session_state: st.session_state["auth_checked"] = False
if "userid" not in st.session_state:
    token = cookie_manager.get("rb_auth_token")
    if token:
        client = get_client()
        res = client.execute("SELECT userid FROM t_users WHERE session_token = ? AND active = 1", [token])
        client.close()
        if res.rows:
            st.session_state["userid"] = res.rows[0][0]
            st.session_state["auth_checked"] = True; st.rerun()
    elif not st.session_state["auth_checked"]:
        st.session_state["auth_checked"] = True; time.sleep(0.5); st.rerun()

if "userid" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>RoadBook Login</h3>", unsafe_allow_html=True)
        u_in = st.text_input("Benutzername")
        p_in = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True, type="primary"):
            if login_user(u_in, p_in): st.rerun()
        st.divider()
        c_reg1, c_reg2 = st.columns(2)
        if c_reg1.button("Neuer User?", use_container_width=True): registration_dialog()
    st.stop()

USER_ID = st.session_state["userid"]

# --- 6. HILFSFUNKTIONEN & DATEN ---
def load_data(search="", limit=400):
    client = get_client()
    query = "SELECT rowid AS id, * FROM t_activities WHERE userid = ?"
    params = [USER_ID]
    if search:
        s = f"%{search}%"
        query += " AND (LOWER(device) LIKE LOWER(?) OR LOWER(cityfrom) LIKE LOWER(?) OR LOWER(details) LIKE LOWER(?))"
        params.extend([s, s, s])
    query += f" ORDER BY date DESC LIMIT {limit}"
    res = client.execute(query, params); df = pd.DataFrame(res.rows, columns=res.columns); client.close()
    return df

def get_default_values():
    client = get_client()
    u_res = client.execute("SELECT weight FROM t_users WHERE userid = ?", [USER_ID])
    u_weight = float(u_res.rows[0][0] or 84.0)
    df_last = load_data(limit=1); client.close()
    if df_last.empty: return {'devs': ["Cube"], 'dist': 20.0, 'time': 60, 'vmax': 25, 'from': "Herzogenaurach", 'weight': u_weight}
    return {'devs': sorted(df_last['device'].unique().tolist()), 'dist': round(df_last['distance'].iloc[0]/1000, 1), 'time': int(df_last['time'].iloc[0]), 'vmax': int(df_last['vmax'].iloc[0]), 'from': df_last['cityfrom'].iloc[0], 'weight': u_weight}

def minutes_to_hm(m): return f"{int(m)//60:02d}:{int(m)%60:02d}"
def hm_to_minutes(s):
    try:
        h, m = map(int, s.split(':')); return h * 60 + m
    except: return 0

# --- 7. SIDEBAR ---
with st.sidebar:
    client = get_client()
    u_res = client.execute("SELECT nickname FROM t_users WHERE userid = ?", [USER_ID])
    nickname = u_res.rows[0][0] if u_res.rows else "User"
    client.close()
    st.title("RoadBook Menü")
    st.info(f"Eingeloggt: **{nickname}**")
    
    if nickname.lower() == ADMIN_NICKNAME.lower():
        if st.button("🛠️ Admin-Bereich", use_container_width=True): admin_dialog()
        st.divider()
        
    if st.button("👤 Profil", use_container_width=True): user_settings_dialog()
    if st.button("🚪 Abmelden", type="secondary", use_container_width=True):
        client = get_client(); client.execute("UPDATE t_users SET session_token = NULL WHERE userid = ?", [USER_ID]); client.close()
        cookie_manager.delete("rb_auth_token"); del st.session_state["userid"]; st.rerun()

# --- 8. HAUPTSEITE LOGIK & DIALOGE ---

@st.dialog("Eintrag bearbeiten")
def activity_dialog(row_id=None):
    is_new = row_id is None
    client = get_client()
    defaults = get_default_values()
    
    if not is_new:
        # Hier nutzen wir rowid AS id, damit wir die ID für das UPDATE haben
        res = client.execute("SELECT rowid AS id, * FROM t_activities WHERE rowid = ? AND userid = ?", [row_id, USER_ID])
        if not res.rows:
            st.error("Datensatz nicht gefunden.")
            client.close()
            return
        row = pd.DataFrame(res.rows, columns=res.columns).iloc[0]
    else:
        # Standardwerte für neuen Eintrag (inklusive cityto)
        row = {'device': defaults['devs'][0], 'date': str(datetime.now().date()), 
               'cityfrom': defaults['from'], 'cityto': '', 'distance': defaults['dist']*1000, 
               'time': defaults['time'], 'details': '', 'vmax': defaults['vmax'], 'weight': defaults['weight']}
    
    with st.form("edit_form", clear_on_submit=True):
        st.subheader("Training bearbeiten" if not is_new else "Neuer Eintrag")
        
        new_dev = st.selectbox("Gerät", defaults['devs'], index=0 if is_new else (defaults['devs'].index(row['device']) if row['device'] in defaults['devs'] else 0))
        
        c1, c2 = st.columns(2)
        new_date = c1.date_input("Datum", value=datetime.strptime(str(row['date']), '%Y-%m-%d'))
        new_from = c1.text_input("Start", value=row['cityfrom'])
        new_to = c1.text_input("Ziel", value=row.get('cityto', '')) # cityto hinzugefügt
        
        new_dist = c2.number_input("Distanz (km)", value=float(row['distance'])/1000.0)
        new_time = c2.text_input("Dauer (hh:mm)", value=minutes_to_hm(row['time']))
        new_vmax = c2.number_input("Vmax", value=int(row['vmax']))
        
        new_details = st.text_area("Details", value=row['details'] or "")
        
        if st.form_submit_button("Speichern", type="primary", use_container_width=True):
            m = hm_to_minutes(new_time)
            # WICHTIG: Die Spaltenliste muss exakt deiner DB-Tabelle entsprechen!
            # Ich füge hier 'cityto' hinzu, da es im Grid abgefragt wird.
            try:
                if is_new:
                    client.execute(
                        "INSERT INTO t_activities (device, date, cityfrom, cityto, distance, time, details, vmax, userid) VALUES (?,?,?,?,?,?,?,?,?)", 
                        [new_dev, str(new_date), new_from, new_to, new_dist*1000, m, new_details, new_vmax, USER_ID]
                    )
                else:
                    client.execute(
                        "UPDATE t_activities SET device=?, date=?, cityfrom=?, cityto=?, distance=?, time=?, details=?, vmax=? WHERE rowid=? AND userid=?", 
                        [new_dev, str(new_date), new_from, new_to, new_dist*1000, m, new_details, new_vmax, row_id, USER_ID]
                    )
                client.close()
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Datenbankfehler: {e}")
                client.close()

        if st.form_submit_button("Abbrechen", use_container_width=True):
            client.close()
            st.query_params.clear()
            st.rerun()
            
# --- TRIGGER ---
st.title("RoadBook Training 🚲")

if "del_id" in st.query_params:
    client = get_client(); client.execute("DELETE FROM t_activities WHERE rowid = ? AND userid = ?", [st.query_params["del_id"], USER_ID]); client.close()
    st.query_params.clear(); st.rerun()

if "edit_id" in st.query_params:
    activity_dialog(st.query_params["edit_id"])

search = st.text_input("Suche", placeholder="Ort, Gerät...", label_visibility="collapsed")

t1, t2 = st.columns([4, 1])
with t2:
    if st.button("➕ Neu", type="primary", use_container_width=True):
        st.query_params.clear()
        activity_dialog()

# --- DATEN-GRID ---
data = load_data(search)
if not data.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Distanz", f"{data['distance'].sum()/1000.0:.1f} km")
    c2.metric("Zeit", minutes_to_hm(data['time'].sum()))
    c3.metric("Max Speed", f"{data['vmax'].max()} km/h")
    
    st.markdown("""<div class="training-grid grid-header"><div class="cell">Aktion</div><div class="cell">Datum</div><div class="cell">Sport</div><div class="cell">Start</div><div class="cell hide-mobile">Ziel</div><div class="cell hide-tablet">KM</div><div class="cell hide-tablet">Zeit</div><div class="cell hide-tablet">Details</div><div class="cell hide-tablet">Vmax</div></div>""", unsafe_allow_html=True)
    for _, r in data.iterrows():
        st.markdown(f"""
        <div class="training-grid">
            <div class="cell">
                <a href="?edit_id={r['id']}" target="_self" class="icon-link">📝</a>
                <a href="?del_id={r['id']}" target="_self" class="icon-link">🗑️</a>
            </div>
            <div class="cell">{str(r['date']).replace('-', '.')}</div>
            <div class="cell">{r['device']}</div>
            <div class="cell">{r['cityfrom']}</div>
            <div class="cell hide-mobile">{r['cityto'] or ''}</div>
            <div class="cell hide-tablet">{r['distance']/1000:.1f}</div>
            <div class="cell hide-tablet">{minutes_to_hm(r['time'])}</div>
            <div class="cell hide-tablet">{r['details'] or ''}</div>
            <div class="cell hide-tablet">{r['vmax']}</div>
        </div>
        """, unsafe_allow_html=True)