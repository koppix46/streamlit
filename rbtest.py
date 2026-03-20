import streamlit as st
import pandas as pd
import numpy as np

# Konfiguration der Seite für bessere mobile Ansicht
st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    # Erstellung eines Beispiel-Datensatzes (25.000 Zeilen, 20 Spalten)
    df = pd.DataFrame(
        np.random.randint(0, 100, size=(25000, 20)),
        columns=[f"Spalte_{i+1}" for i in range(20)]
    )
    df.insert(0, "ID", range(1, 25001))
    return df

data = load_data()

st.title("🚀 Mobile-Ready Data Editor")

# --- Responsive UI Steuerung ---
with st.sidebar:
    st.header("Anzeige-Optionen")
    # Simulation der Footables-Logik: Wichtigste Spalten vordefinieren
    default_cols = ["ID", "Spalte_1", "Spalte_2", "Spalte_3"]
    selected_columns = st.multiselect(
        "Spalten wählen", 
        options=data.columns.tolist(), 
        default=default_cols
    )

# --- Tabelle (Data Editor) ---
# Nutzung von 'on_select', um Interaktionen (Klick auf Zeile) abzufangen
event = st.dataframe(
    data[selected_columns],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",  # Ermöglicht Reaktion auf Zeilenauswahl
    selection_mode="single-row"
)

# --- Detail-Ansicht (Footables Ersatz für Mobile) ---
# Wenn eine Zeile ausgewählt wurde, zeigen wir ALLE 20 Spalten übersichtlich an
if event and len(event.selection.rows) > 0:
    selected_idx = event.selection.rows[0]
    row_data = data.iloc[selected_idx]
    
    st.divider()
    st.subheader(f"📝 Details & Bearbeitung: Datensatz {row_data['ID']}")
    
    # Mobil-optimiertes Layout: Spalten werden untereinander angezeigt
    with st.expander("Alle Spalten anzeigen/bearbeiten", expanded=True):
        with st.form("edit_form"):
            # Hier könnten alle 20 Spalten als Eingabefelder stehen
            cols = st.columns(2) # Auf Desktop 2-spaltig, auf Mobile untereinander
            for i, col_name in enumerate(data.columns):
                with cols[i % 2]:
                    st.text_input(col_name, value=row_data[col_name])
            
            if st.form_submit_button("Änderungen speichern"):
                st.success(f"Datensatz {row_data['ID']} wurde aktualisiert!")
else:
    st.info("💡 Tipp: Klicke auf eine Zeile in der Tabelle, um alle Details mobiloptimiert zu bearbeiten.")
