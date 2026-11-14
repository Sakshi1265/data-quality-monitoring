import sqlite3

conn = sqlite3.connect("reports/quality.db")
cursor = conn.cursor()

tables = [
    "pipeline_runs",
    "baseline_profiles",
    "data_quality_alerts",
    "rejected_records",
    "orders"
]

for table in tables:
    print("\nTABLE:", table)

    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]

    print("Total Records:", count)

    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
    rows = cursor.fetchall()

    for row in rows:
        print(row)

conn.close()
