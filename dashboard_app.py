import os
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Northwind Sales OLAP Dashboard", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent


def find_duckdb_path():
    candidates = [
        os.getenv("DUCKDB_PATH"),
        str(PROJECT_ROOT / "northwindDW_duckdb" / "target" / "duckdb" / "northwind.duckdb"),
        str(PROJECT_ROOT / "northwindDW_duckdb" / "northwind.duckdb"),
        str(PROJECT_ROOT / "northwind.duckdb"),
        str(PROJECT_ROOT / "warehouse.duckdb"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def create_sample_data():
    rng = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    rows = []

    product_names = {
        1: "Chai",
        2: "Chang",
        3: "Aniseed Syrup",
        4: "Chef Anton's Cajun Seasoning",
        5: "Chef Anton's Gumbo Mix",
        6: "Grandma's Boysenberry Spread",
        7: "Uncle Bob's Organic Dried Pears",
        8: "Northwoods Cranberry Sauce",
        9: "Mishi Kobe Niku",
        10: "Ikura",
    }

    product_category = {
        1: "Beverages",
        2: "Beverages",
        3: "Condiments",
        4: "Seasonings",
        5: "Seasonings",
        6: "Condiments",
        7: "Produce",
        8: "Condiments",
        9: "Meat",
        10: "Seafood",
    }

    customer_names = {i: f"Customer {i}" for i in range(1, 26)}
    employee_names = {i: f"Employee {i}" for i in range(1, 9)}

    for d in rng:
        for product_id in range(1, 11):
            for customer_id in range(1, 26):
                if (product_id + customer_id + d.day) % 5 == 0:
                    continue

                quantity = (customer_id + product_id + d.day) % 10 + 1
                unit_price = 10 + product_id * 5 + (customer_id % 7) * 2
                discount = ((customer_id + product_id) % 15) / 100
                revenue = quantity * unit_price * (1 - discount)

                employee_id = ((customer_id + d.day) % 8) + 1

                rows.append(
                    {
                        "order_id": len(rows) + 1,
                        "product_id": product_id,
                        "product_name": product_names.get(product_id, f"Product {product_id}"),
                        "product_category": product_category.get(product_id, "General"),
                        "customer_id": customer_id,
                        "customer_name": customer_names.get(customer_id, f"Customer {customer_id}"),
                        "employee_id": employee_id,
                        "employee_name": employee_names.get(employee_id, f"Employee {employee_id}"),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "discount": discount,
                        "order_date": d,
                        "year": d.year,
                        "quarter": d.quarter,
                        "quarter_label": f"Q{d.quarter}",
                        "month": d.month,
                        "month_name": d.strftime("%B"),
                        "day_name": d.strftime("%A"),
                        "day_is_weekday": int(d.weekday() < 5),
                        "revenue": revenue,
                    }
                )

    return pd.DataFrame(rows)


def list_tables(con):
    return [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    ]


def resolve_dim_table_name(tables, candidates):
    for candidate in candidates:
        for table in tables:
            if table.lower() == candidate.lower():
                return table
    return None


@st.cache_data
def load_data():
    db_path = find_duckdb_path()

    if db_path:
        try:
            con = duckdb.connect(db_path)
            tables = list_tables(con)

            fact_table = "fact_sales" if "fact_sales" in tables else None
            if fact_table:
                dim_date = resolve_dim_table_name(tables, ["dim_date"])
                dim_customers = resolve_dim_table_name(tables, ["dim_customers"])
                dim_products = resolve_dim_table_name(tables, ["dim_products"])
                dim_employees = resolve_dim_table_name(tables, ["dim_employees", "dim_employee"])

                if dim_date and dim_customers and dim_products and dim_employees:
                    query = f"""
                        SELECT
                            f.order_id,
                            f.order_date,
                            d.id AS date_id,
                            d.full_date,
                            d.year,
                            d.month,
                            d.month_name,
                            d.quarter,
                            d.day_name,
                            d.day_is_weekday,
                            dc.customer_id,
                            dc.customer_name,
                            dp.product_id,
                            dp.product_name,
                            dp.category AS product_category,
                            de.employee_id,
                            de.employee_name,
                            f.quantity,
                            f.unit_price,
                            f.discount,
                            (f.quantity * f.unit_price * (1 - COALESCE(f.discount, 0))) AS revenue
                        FROM {fact_table} f
                        LEFT JOIN {dim_date} d
                            ON CAST(f.order_date AS VARCHAR) = d.id
                        LEFT JOIN {dim_customers} dc
                            ON dc.customer_id = f.customer_id
                        LEFT JOIN {dim_products} dp
                            ON dp.product_id = f.product_id
                        LEFT JOIN {dim_employees} de
                            ON de.employee_id = f.employee_id
                    """
                    df = con.execute(query).fetchdf()
                    if not df.empty:
                        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
                        if "full_date" in df.columns:
                            df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")
                        df["revenue"] = df["revenue"].fillna(0)
                        return enrich_dimensions(df)
        except Exception:
            st.warning("Could not read warehouse tables. Using sample data instead.")

    return enrich_dimensions(create_sample_data())


def enrich_dimensions(df):
    if "order_date" in df.columns and df["order_date"].notna().any():
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["year"] = df["order_date"].dt.year
        df["quarter"] = df["order_date"].dt.quarter
        df["quarter_label"] = "Q" + df["quarter"].astype(str)
        df["month"] = df["order_date"].dt.month
        df["month_name"] = df["order_date"].dt.strftime("%B")
        df["day_name"] = df["order_date"].dt.strftime("%A")
        df["day_is_weekday"] = (df["order_date"].dt.weekday < 5).astype(int)
        df["day_type"] = df["day_is_weekday"].map({1: "Weekday", 0: "Weekend"})
        df["date_label"] = df["order_date"].dt.strftime("%Y-%m-%d")

    if "product_name" in df.columns and "product_category" not in df.columns:
        df["product_category"] = "General"

    if "quantity" not in df.columns:
        df["quantity"] = 1

    if "revenue" not in df.columns:
        df["revenue"] = 0.0

    return df


def apply_filters(df):
    st.sidebar.header("Filters")

    if "order_date" in df.columns:
        min_date = pd.to_datetime(df["order_date"]).min().date()
        max_date = pd.to_datetime(df["order_date"]).max().date()
        start_date = st.sidebar.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End date", max_date, min_value=min_date, max_value=max_date)
        df = df[
            (pd.to_datetime(df["order_date"]).dt.date >= start_date) &
            (pd.to_datetime(df["order_date"]).dt.date <= end_date)
        ]

    for col in ["product_name", "product_category", "customer_name", "employee_name", "month_name", "day_name", "day_type"]:
        if col in df.columns:
            values = sorted(df[col].dropna().astype(str).unique().tolist())
            if values:
                selected = st.sidebar.multiselect(col.replace("_", " ").title(), values, default=values)
                df = df[df[col].astype(str).isin(selected)]

    return df


def build_time_chart(df, level, metric):
    if level == "year":
        group_col = "year"
    elif level == "quarter":
        group_col = "quarter_label"
    elif level == "month":
        group_col = "month_name"
    elif level == "day":
        group_col = "date_label"
    elif level == "weekday":
        group_col = "day_type"
    else:
        group_col = "year"

    if metric == "Revenue":
        value_col = "revenue"
    elif metric == "Quantity":
        value_col = "quantity"
    else:
        value_col = "revenue"

    grouped = (
        df.groupby(group_col, as_index=False)
        .agg(value=(value_col, "sum"), orders=("order_id", "nunique"))
        .rename(columns={group_col: "label"})
    )

    return grouped.sort_values("label")


def build_product_chart(df, level, metric):
    if level == "product line":
        group_col = "product_category"
    elif level == "product":
        group_col = "product_name"
    else:
        group_col = "product_category"

    if metric == "Revenue":
        value_col = "revenue"
    elif metric == "Quantity":
        value_col = "quantity"
    else:
        value_col = "revenue"

    grouped = (
        df.groupby(group_col, as_index=False)
        .agg(value=(value_col, "sum"), orders=("order_id", "nunique"))
        .rename(columns={group_col: "label"})
    )

    return grouped.sort_values("value", ascending=False).head(10)


def main():
    st.title("Northwind Sales OLAP Dashboard(G6)")
    st.caption("Operate at different levels: year, quarter, month, day, weekday/weekend, and product line/product")

    df = load_data()
    df = apply_filters(df)

    if df.empty:
        st.warning("No data matches the selected filters.")
        return

    revenue = df["revenue"].sum()
    quantity = df["quantity"].sum()
    orders = df["order_id"].nunique()
    avg_order = revenue / orders if orders else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"${revenue:,.2f}")
    c2.metric("Quantity", f"{quantity:,.0f}")
    c3.metric("Orders", f"{orders:,.0f}")
    c4.metric("Avg Order Value", f"${avg_order:,.2f}")

    st.sidebar.header("OLAP Views")
    time_level = st.sidebar.selectbox("Time level", ["year", "quarter", "month", "day", "weekday"], index=0)
    time_metric = st.sidebar.selectbox("Time metric", ["Revenue", "Quantity"], index=0)

    product_level = st.sidebar.selectbox("Product level", ["product line", "product"], index=0)
    product_metric = st.sidebar.selectbox("Product metric", ["Revenue", "Quantity"], index=0)

    time_df = build_time_chart(df, time_level, time_metric)
    product_df = build_product_chart(df, product_level, product_metric)

    st.subheader(f"Time view by {time_level}")
    time_chart = (
        alt.Chart(time_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("label:N", title=time_level),
            y=alt.Y("value:Q", title=time_metric),
            tooltip=["label:N", "value:Q"],
        )
        .properties(height=350)
    )
    st.altair_chart(time_chart, use_container_width=True)

    st.subheader(f"Product view by {product_level}")
    product_chart = (
        alt.Chart(product_df)
        .mark_bar()
        .encode(
            x=alt.X("label:N", sort="-y", title=product_level),
            y=alt.Y("value:Q", title=product_metric),
            tooltip=["label:N", "value:Q"],
        )
        .properties(height=350)
    )
    st.altair_chart(product_chart, use_container_width=True)

    st.subheader("Detail table")
    st.dataframe(df.head(200), use_container_width=True)


if __name__ == "__main__":
    main()