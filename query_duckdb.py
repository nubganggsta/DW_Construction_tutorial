# ...existing code...
import duckdb
import pandas as pd
from pathlib import Path


DB_PATH = Path("northwindDW_duckdb/dev.duckdb")
DATASETS_DIR = Path("northwindDW_duckdb/datasets")


conn = duckdb.connect(str(DB_PATH))


all_tables_df = conn.execute(
    """
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = 'main'
      AND table_name NOT LIKE 'sqlite_%'
    ORDER BY table_name
    """
).fetch_df()


print("Tables in dev.duckdb:")
print(all_tables_df.to_string(index=False))


print("\n" + "=" * 80)
print("CSV files in datasets folder:")
print("=" * 80)
for csv_file in sorted(DATASETS_DIR.glob("*.csv")):
    print(f"  - {csv_file.name}")


print("\n" + "=" * 80)
print("Preview: stg_customers")
print("=" * 80)


try:
    result = conn.execute('SELECT * FROM "main"."stg_customers" LIMIT 20').fetchall()
except Exception as e:
    msg = str(e)
    if "No files found that match the pattern" in msg or "IO Error" in msg:
        # try to find a matching CSV in the known datasets directory and recreate view
        candidates = list(DATASETS_DIR.glob("*customer*.csv")) + list(DATASETS_DIR.glob("*customers*.csv"))
        if not candidates:
            raise
        csv_path = candidates[0].resolve()
        conn.execute(
            f'CREATE OR REPLACE VIEW "main"."stg_customers" AS SELECT * FROM read_csv_auto(\'{csv_path.as_posix()}\')'
        )
        result = conn.execute('SELECT * FROM "main"."stg_customers" LIMIT 20').fetchall()
    else:
        raise


df = pd.DataFrame(result, columns=[desc[0] for desc in conn.description])
print(df)


conn.close()
# ...existing code...
