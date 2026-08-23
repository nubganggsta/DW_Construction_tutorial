import os
from pathlib import Path
import streamlit as st
import duckdb
import pandas as pd


# Page config
st.set_page_config(
    page_title="Northwind DW Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)


DB_PATH = "northwindDW_duckdb/dev.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


def run_query(query):
    conn = get_connection()
    try:
        return conn.execute(query).fetch_df()
    except Exception as e:
        st.error(f"Error running query: {e}")
        return pd.DataFrame()


st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


st.markdown('<div class="main-title">📊 Northwind DW Explorer(Group 6)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Inspect and preview raw datasets, staging tables, and dimension views in dev.duckdb</div>', unsafe_allow_html=True)


tables_df = run_query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name")
all_tables = tables_df['table_name'].tolist() if not tables_df.empty else []


# show both stg_ and dim_ tables
tables = [t for t in all_tables if t.startswith("stg_") or t.startswith("dim_")]


if not tables:
    st.warning("No tables found in the database. Please make sure the dbt run was successful.")
else:
    table_stats = []
    for t in tables:
        count_df = run_query(f"SELECT COUNT(*) as count FROM main.{t}")
        count = count_df['count'].iloc[0] if not count_df.empty else 0
        table_stats.append({"table_name": t, "row_count": count})


    stats_df = pd.DataFrame(table_stats)


    st.sidebar.title("🗂️ Table Browser")
    selected_table = st.sidebar.selectbox("Select a table to inspect", tables)


    st.sidebar.markdown("---")
    st.sidebar.subheader("Quick Stats")
    st.sidebar.markdown(f"**Total Tables:** {len(tables)}")
    st.sidebar.markdown(f"**Total Rows:** {stats_df['row_count'].sum():,}")


    tab1, tab2 = st.tabs(["📋 Database Schema & Overview", "🔍 Data Viewer & Metadata"])


    with tab1:
        st.subheader("Database Tables Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Tables", len(tables))
        with col2:
            st.metric("Total Records", f"{stats_df['row_count'].sum():,}")


        st.markdown("### Table List & Record Counts")
        st.dataframe(
            stats_df.rename(columns={"table_name": "Table Name", "row_count": "Row Count"}),
            use_container_width=True,
            hide_index=True
        )


    with tab2:
        st.subheader(f"Table Details: `{selected_table}`")
        cols_df = run_query(f"PRAGMA table_info('{selected_table}')")


        col1, col2 = st.columns([1, 3])
        with col1:
            st.write("**Table Summary**")
            row_cnt = stats_df.loc[stats_df['table_name'] == selected_table, 'row_count'].iloc[0]
            st.write(f"- **Rows**: `{row_cnt}`")
            st.write(f"- **Columns**: `{len(cols_df)}`")
            st.markdown("---")
            st.write("**Columns & Types**")
            if not cols_df.empty:
                st.dataframe(
                    cols_df[['name', 'type']].rename(columns={"name": "Column", "type": "Type"}),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.write("No column info available.")


        with col2:
            st.write("**Data Preview (First 100 rows)**")
            data_df = run_query(f"SELECT * FROM main.{selected_table} LIMIT 100")
            st.dataframe(data_df, use_container_width=True, hide_index=True)


            csv_data = data_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download `{selected_table}` as CSV",
                data=csv_data,
                file_name=f"{selected_table}_preview.csv",
                mime="text/csv"
            )
