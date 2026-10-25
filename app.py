import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "flock_screenings.db"

st.set_page_config(
    page_title="FlockCare | Screening Dashboard",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1450px;}
.hero {
    padding: 1.35rem 1.5rem;
    border-radius: 18px;
    background: linear-gradient(115deg, rgba(21,128,61,.14), rgba(14,165,233,.10));
    border: 1px solid rgba(100,116,139,.22);
    margin-bottom: 1.2rem;
}
.hero h1 {margin: 0 0 .35rem 0; font-size: 2rem;}
.hero p {margin: 0; color: #64748b;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 14px 16px;
}
.small-note {color: #64748b; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)


def connect():
    return sqlite3.connect(DB_PATH, timeout=15)


def initialize_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bird_id TEXT NOT NULL,
                flock_id TEXT NOT NULL,
                screening_date TEXT NOT NULL,
                symptoms TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL CHECK(result IN ('Normal', 'Flagged for Review')),
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_record(bird_id, flock_id, screening_date, symptoms, result, notes):
    with connect() as conn:
        conn.execute("""
            INSERT INTO screenings
            (bird_id, flock_id, screening_date, symptoms, result, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (bird_id.strip(), flock_id.strip(), screening_date.isoformat(),
              symptoms.strip(), result, notes.strip()))


def get_records():
    with connect() as conn:
        return pd.read_sql_query("""
            SELECT id, bird_id, flock_id, screening_date, symptoms, result, notes, created_at
            FROM screenings
            ORDER BY screening_date DESC, id DESC
        """, conn)


def remove_record(record_id):
    with connect() as conn:
        conn.execute("DELETE FROM screenings WHERE id = ?", (int(record_id),))


initialize_db()
df = get_records()

with st.sidebar:
    st.markdown("## 🐔 FlockCare")
    st.caption("Bird screening record system")
    page = st.radio(
        "MENU",
        ["Dashboard", "Add screening", "Screening history", "Project information"],
        label_visibility="visible",
    )
    st.divider()
    st.markdown("**Storage status**")
    st.success("Local database ready")
    st.caption("Records are saved in `flock_screenings.db`.")
    st.caption("Back up this file regularly.")

st.markdown("""
<div class="hero">
  <h1>Flock Screening Dashboard</h1>
  <p>Record observations, review flock history, and track birds flagged for follow-up.</p>
</div>
""", unsafe_allow_html=True)

if page == "Dashboard":
    st.subheader("At a glance")
    if df.empty:
        a, b, c = st.columns(3)
        a.metric("Screening records", "0")
        b.metric("Unique birds screened", "0")
        c.metric("Flagged for review", "0")
        st.info("No screening records yet. Select **Add screening** in the sidebar to enter your first observation.")
        st.markdown("#### Your dashboard will show")
        st.write("- Total screening records and unique birds")
        st.write("- Number of records flagged for review")
        st.write("- Flock-level screening history")
        st.write("- Charts showing flagged observations over time")
    else:
        df["screening_date"] = pd.to_datetime(df["screening_date"], errors="coerce")
        total_records = int(len(df))
        unique_birds = int(df["bird_id"].nunique())
        unique_flocks = int(df["flock_id"].nunique())
        flagged_count = int((df["result"] == "Flagged for Review").sum())
        normal_count = int((df["result"] == "Normal").sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Screenings recorded", f"{total_records:,}")
        m2.metric("Unique birds", f"{unique_birds:,}")
        m3.metric("Flocks screened", f"{unique_flocks:,}")
        m4.metric("Flagged records", f"{flagged_count:,}", delta=f"{flagged_count} need review" if flagged_count else "None flagged", delta_color="inverse")

        st.divider()
        left, right = st.columns([1.35, 1])
        with left:
            st.markdown("#### Flagged observations over time")
            flagged_df = df[df["result"] == "Flagged for Review"].dropna(subset=["screening_date"])
            if flagged_df.empty:
                st.info("No flagged observations recorded so far.")
            else:
                daily = flagged_df.groupby(flagged_df["screening_date"].dt.date).size()
                daily.index = pd.to_datetime(daily.index)
                daily = daily.rename("Flagged observations").to_frame()
                st.line_chart(daily, use_container_width=True)
        with right:
            st.markdown("#### Screening results")
            counts = df["result"].value_counts().reindex(
                ["Normal", "Flagged for Review"], fill_value=0
            ).rename_axis("Result").to_frame("Records")
            st.bar_chart(counts, use_container_width=True)

        st.markdown("#### Flocks with flagged observations")
        flagged_flocks = (
            df[df["result"] == "Flagged for Review"]
            .groupby("flock_id").size().sort_values(ascending=False)
            .rename("Flagged records").to_frame()
        )
        if flagged_flocks.empty:
            st.success("No flagged records to review.")
        else:
            st.dataframe(flagged_flocks, use_container_width=True)

        st.markdown("#### Latest screening records")
        recent = df.head(8).copy()
        recent["screening_date"] = recent["screening_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            recent[["bird_id", "flock_id", "screening_date", "symptoms", "result"]],
            use_container_width=True, hide_index=True
        )

elif page == "Add screening":
    st.subheader("Add a screening record")
    st.write("Complete the details below. Bird ID and Flock ID are required.")
    with st.form("screening_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            bird_id = st.text_input("Bird ID *", placeholder="Example: B001")
            flock_id = st.text_input("Flock ID *", placeholder="Example: FLOCK-A")
            screening_date = st.date_input("Screening date")
        with col2:
            result = st.selectbox("Screening result *", ["Normal", "Flagged for Review"])
            symptoms = st.text_area("Symptoms / observations", placeholder="Example: reduced activity, eye discharge")
        notes = st.text_area("Additional notes (optional)", placeholder="Any details for follow-up")
        submitted = st.form_submit_button("Save screening record", type="primary", use_container_width=True)
        if submitted:
            if not bird_id.strip() or not flock_id.strip():
                st.error("Please enter both Bird ID and Flock ID.")
            else:
                add_record(bird_id, flock_id, screening_date, symptoms, result, notes)
                st.success("Record saved successfully.")
                st.rerun()

elif page == "Screening history":
    st.subheader("Screening history")
    if df.empty:
        st.info("No records are saved yet. Add a screening to begin your history.")
    else:
        f1, f2, f3 = st.columns([1, 1, 1.3])
        with f1:
            flock_options = ["All flocks"] + sorted(df["flock_id"].dropna().unique().tolist())
            flock_filter = st.selectbox("Flock", flock_options)
        with f2:
            result_filter = st.selectbox("Result", ["All results", "Normal", "Flagged for Review"])
        with f3:
            search = st.text_input("Search bird ID or symptoms", placeholder="Type a keyword")

        filtered = df.copy()
        if flock_filter != "All flocks":
            filtered = filtered[filtered["flock_id"] == flock_filter]
        if result_filter != "All results":
            filtered = filtered[filtered["result"] == result_filter]
        if search.strip():
            q = search.strip().lower()
            matches = (
                filtered["bird_id"].fillna("").str.lower().str.contains(q, regex=False)
                | filtered["symptoms"].fillna("").str.lower().str.contains(q, regex=False)
                | filtered["notes"].fillna("").str.lower().str.contains(q, regex=False)
            )
            filtered = filtered[matches]

        st.caption(f"{len(filtered)} record(s) shown out of {len(df)} total.")
        view = filtered[["id", "bird_id", "flock_id", "screening_date", "symptoms", "result", "notes"]]
        st.dataframe(view, use_container_width=True, hide_index=True)

        st.download_button(
            "Download records as CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="flock_screening_records.csv",
            mime="text/csv",
        )

        with st.expander("Delete a record"):
            st.warning("Deletion is permanent. Only delete a record if you are sure.")
            ids = filtered["id"].astype(int).tolist()
            if ids:
                record_id = st.selectbox("Choose record ID", ids)
                confirm = st.checkbox("I confirm that I want to delete this record.")
                if st.button("Delete selected record", disabled=not confirm):
                    remove_record(record_id)
                    st.success(f"Record #{record_id} deleted.")
                    st.rerun()

elif page == "Project information":
    st.subheader("About this project")
    st.markdown("""
    **Purpose:** provide a simple record system for bird screening and help a farmer review observations across flocks.

    **Record fields**
    - Bird ID
    - Flock ID
    - Screening date
    - Symptoms / observations
    - Screening result (`Normal` or `Flagged for Review`)
    - Optional notes

    **Technology used**
    - Python for application logic
    - Streamlit for the web interface
    - pandas for filtering and summaries
    - SQLite for persistent storage
    - Streamlit charts for trend visualization
    """)
    st.warning("A 'Flagged for Review' screening result is not a confirmed disease diagnosis.")
    st.markdown("#### Persistence check")
    st.write("1. Add a test record.")
    st.write("2. Stop and restart the app.")
    st.write("3. Open Screening history and confirm the record is still there.")
    st.write("The database is local to this computer. A shared online deployment needs hosted persistent storage.")
    st.markdown("#### Start the app")
    st.code("pip install -r requirements.txt\nstreamlit run app.py", language="bash")

st.divider()
st.markdown(
    '<p class="small-note">FlockCare demo · Keep the database backed up. Screening flags are for review, not diagnosis.</p>',
    unsafe_allow_html=True,
)
