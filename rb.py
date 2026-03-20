import sqlite3
import streamlit as st
from datetime import datetime

DB_PATH = "roadbook.sqlite"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS t_activities (
                device NUMERIC NOT NULL,
                userid NUMERIC NOT NULL,
                cityfrom NUMERIC NOT NULL,
                cityto NUMERIC NOT NULL,
                date DATETIME NOT NULL,
                distance REAL NOT NULL,
                time INTEGER NOT NULL,
                details TEXT,
                vmax INTEGER,
                weight REAL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def fetch_all():
    conn = get_connection()
    try:
        cur = conn.execute("SELECT rowid, * FROM t_activities WHERE userid = 2 ORDER BY date DESC")
        return cur.fetchall()
    finally:
        conn.close()


def insert_record(data):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO t_activities (device, userid, cityfrom, cityto, date, distance, time, details, vmax, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["device"],
                data["userid"],
                data["cityfrom"],
                data["cityto"],
                data["date"],
                data["distance"],
                data["time"],
                data["details"],
                data["vmax"],
                data["weight"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_record(rowid, data):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE t_activities
            SET device = ?, userid = ?, cityfrom = ?, cityto = ?, date = ?, distance = ?, time = ?, details = ?, vmax = ?, weight = ?
            WHERE rowid = ?
            """,
            (
                data["device"],
                data["userid"],
                data["cityfrom"],
                data["cityto"],
                data["date"],
                data["distance"],
                data["time"],
                data["details"],
                data["vmax"],
                data["weight"],
                rowid,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_record(rowid):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM t_activities WHERE rowid = ?", (rowid,))
        conn.commit()
    finally:
        conn.close()


def format_duration(minutes):
    try:
        total_minutes = int(minutes)
    except (TypeError, ValueError):
        return "00:00"
    hours = total_minutes // 60
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"


def record_form(key, data=None):
    if data is None:
        data = {
            "device": "",
            "userid": 2,
            "cityfrom": "",
            "cityto": "",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "distance": 0.0,
            "time": 0,
            "details": "",
            "vmax": 0,
            "weight": 0.0,
        }

    with st.form(f"form_{key}"):
        cols = st.columns(2)
        with cols[0]:
            device = st.text_input("Sportgerät", value=str(data["device"]), key=f"device_{key}")
            cityfrom = st.text_input("Start", value=str(data["cityfrom"]), key=f"cityfrom_{key}")
            cityto = st.text_input("Ziel", value=str(data["cityto"]), key=f"cityto_{key}")
            date = st.text_input("Datum (YYYY-MM-DD HH:MM)", value=str(data["date"]), key=f"date_{key}")
            userid = st.number_input("User ID", value=1, min_value=1, max_value=1, step=0, key=f"userid_{key}", disabled=True)
        with cols[1]:
            distance = st.number_input("Entfernung (km)", value=float(data.get("distance", 0.0)), min_value=0.0, step=0.1, key=f"distance_{key}")
            time_val = st.number_input("Dauer (Minuten)", value=int(data.get("time", 0)), min_value=0, step=1, key=f"time_{key}")
            weight = st.number_input("Gewicht (kg)", value=float(data.get("weight", 0.0)), min_value=0.0, step=0.1, key=f"weight_{key}")
            vmax = st.number_input("vmax (km/h)", value=int(data.get("vmax", 0)), min_value=0, step=1, key=f"vmax_{key}")
            details = st.text_area("Details", value=str(data.get("details", "")), key=f"details_{key}")

        submitted = st.form_submit_button("Speichern")
        if submitted:
            return {
                "device": device,
                "userid": userid,
                "cityfrom": cityfrom,
                "cityto": cityto,
                "date": date,
                "distance": distance,
                "time": time_val,
                "details": details,
                "vmax": vmax,
                "weight": weight,
            }
    return None


def main():
    st.set_page_config(page_title="RoadBook Trainingstagebuch", layout="wide")
    st.title("RoadBook Trainingstagebuch")
    st.markdown("## Hans-Jürgen's Tracking Tool")
    st.markdown("App-Name: `rb.py` | SQLite3 DB: `roadbook.sqlite`")

    init_db()

    with st.expander("Neuen Datensatz hinzufügen", expanded=True):
        new_data = record_form("neu")
        if new_data:
            insert_record(new_data)
            st.success("Neuer Datensatz hinzugefügt")
            st.rerun()

    st.markdown("---")
    st.subheader("Datagrid")
    search = st.text_input("Search", value="", help="Filter nach Datum, Sportgerät, Start, Ziel, Details")

    rows = fetch_all()
    if search:
        search_lower = search.strip().lower()
        rows = [
            r
            for r in rows
            if search_lower in str(r["date"]).lower()
            or search_lower in str(r["device"]).lower()
            or search_lower in str(r["cityfrom"]).lower()
            or search_lower in str(r["cityto"]).lower()
            or search_lower in str(r["details"]).lower()
        ]

    count_rows = len(rows)
    st.write(f"Aktuelle Datensätze (userid = 1): {count_rows}")
    if count_rows == 0:
        st.warning("Es sind keine Datensätze mit userid = 1 vorhanden. Bitte Datensätze hinzufügen oder userid prüfen.")

    header_cols = st.columns([1.2, 1.1, 1.1, 1.1, 0.9, 0.9, 0.9, 0.9, 1.5])
    header_cols[0].markdown("**Datum**")
    header_cols[1].markdown("**Sportgerät**")
    header_cols[2].markdown("**Start**")
    header_cols[3].markdown("**Ziel**")
    header_cols[4].markdown("**Entfernung (km)**")
    header_cols[5].markdown("**Dauer**")
    header_cols[6].markdown("**Gewicht (kg)**")
    header_cols[7].markdown("**vmax**")
    header_cols[8].markdown("**Aktion**")

    for row in rows:
        rowid = row["rowid"]
        row_data = {
            "device": row["device"],
            "userid": row["userid"],
            "cityfrom": row["cityfrom"],
            "cityto": row["cityto"],
            "date": row["date"],
            "distance": row["distance"],
            "time": row["time"],
            "details": row["details"],
            "vmax": row["vmax"],
            "weight": row["weight"],
        }

        cols = st.columns([1.2, 1.1, 1.1, 1.1, 0.9, 0.9, 0.9, 0.9, 1.5])
        cols[0].write(row_data["date"])
        cols[1].write(row_data["device"])
        cols[2].write(row_data["cityfrom"])
        cols[3].write(row_data["cityto"])
        cols[4].write(row_data["distance"])
        cols[5].write(format_duration(row_data["time"]))
        cols[6].write(row_data["weight"])
        cols[7].write(row_data["vmax"])

        if cols[8].button("Löschen", key=f"delete_{rowid}"):
            delete_record(rowid)
            st.success(f"Datensatz {rowid} gelöscht")
            st.rerun()

        if cols[8].button("Bearbeiten", key=f"edit_btn_{rowid}"):
            st.session_state[f"edit_mode_{rowid}"] = True
            st.rerun()

        if st.session_state.get(f"edit_mode_{rowid}", False):
            with st.expander(f"bearbeite Datensatz: {rowid}", expanded=True):
                updated = record_form(f"edit_{rowid}", data=row_data)
                if updated:
                    update_record(rowid, updated)
                    st.session_state[f"edit_mode_{rowid}"] = False
                    st.success(f"Datensatz {rowid} aktualisiert")
                    st.rerun()


if __name__ == "__main__":
    main()