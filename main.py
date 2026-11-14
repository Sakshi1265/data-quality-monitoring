
import pandas as pd
import sqlite3
import os

# Create reports folder
os.makedirs("reports", exist_ok=True)

# Connect to SQLite database
conn = sqlite3.connect("reports/quality.db")
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    source_file TEXT,
    total_rows INTEGER,
    valid_rows INTEGER,
    rejected_rows INTEGER,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS baseline_profiles (
    metric TEXT PRIMARY KEY,
    metric_value REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS data_quality_alerts (
    run_id TEXT,
    metric TEXT,
    baseline_value REAL,
    current_value REAL,
    explanation TEXT,
    severity TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS rejected_records (
    run_id TEXT,
    source_file TEXT,
    order_id INTEGER,
    reason TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id TEXT,
    order_amount REAL,
    city TEXT,
    order_date TEXT,
    run_id TEXT
)
""")

conn.commit()


def read_data(file_path):

    df = pd.read_csv(file_path)

    print("\nReading file:", file_path)
    print("Total records:", len(df))

    return df


def validate_data(df):

    df = df.copy()

    required_columns = [
        "order_id",
        "customer_id",
        "order_amount",
        "city",
        "order_date"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    df["order_date"] = pd.to_datetime(
        df["order_date"], errors="coerce"
    )

    reasons = []

    for _, row in df.iterrows():

        error = []

        if pd.isna(row["customer_id"]):
            error.append("Missing customer_id")

        if pd.isna(row["order_id"]):
            error.append("Missing order_id")

        if pd.isna(row["order_amount"]):
            error.append("Missing order_amount")

        elif row["order_amount"] < 0:
            error.append("Negative order amount")

        if pd.isna(row["order_date"]):
            error.append("Invalid order date")

        reasons.append(", ".join(error))

    df["rejection_reason"] = reasons

    # Check duplicate order IDs
    duplicates = df["order_id"].duplicated(
        keep="first"
    )

    for index in df[duplicates].index:

        if df.loc[index, "rejection_reason"]:
            df.loc[index, "rejection_reason"] += (
                ", Duplicate order_id"
            )
        else:
            df.loc[index, "rejection_reason"] = (
                "Duplicate order_id"
            )

    valid_data = df[
        df["rejection_reason"] == ""
    ].copy()

    rejected_data = df[
        df["rejection_reason"] != ""
    ].copy()

    return valid_data, rejected_data


def create_profile(df):

    profile = {
        "total_rows": len(df),

        "null_rate": (
            df["customer_id"].isna().mean() * 100
        ),

        "average_amount": (
            df["order_amount"].mean()
        ),

        "latest_date": (
            pd.to_datetime(
                df["order_date"]
            ).max()
        )
    }

    return profile


def save_baseline(profile):

    metrics = {
        "total_rows": profile["total_rows"],
        "null_rate": profile["null_rate"],
        "average_amount": profile["average_amount"]
    }

    for metric, value in metrics.items():

        cursor.execute("""
        INSERT OR REPLACE INTO baseline_profiles
        VALUES (?, ?)
        """, (metric, float(value)))

    conn.commit()

    print("\nBaseline profile saved successfully!")


def compare_data(profile, run_id):

    cursor.execute("""
    SELECT metric, metric_value
    FROM baseline_profiles
    """)

    baseline = dict(cursor.fetchall())

    alerts = []

    # Volume comparison
    old_rows = baseline["total_rows"]
    new_rows = profile["total_rows"]

    change = (
        abs(new_rows - old_rows) /
        max(old_rows, 1) * 100
    )

    if change > 20:

        alerts.append((
            "Volume",
            old_rows,
            new_rows,
            f"Row count changed by {change:.2f}%",
            "WARNING"
        ))

    # Null rate comparison
    old_null = baseline["null_rate"]
    new_null = profile["null_rate"]

    if new_null > old_null + 5:

        alerts.append((
            "Null Rate",
            old_null,
            new_null,
            f"Null rate increased from {old_null:.2f}% to {new_null:.2f}%",
            "CRITICAL"
        ))

    # Distribution comparison
    old_avg = baseline["average_amount"]
    new_avg = profile["average_amount"]

    if old_avg != 0:

        amount_change = (
            abs(new_avg - old_avg) /
            abs(old_avg) * 100
        )

        if amount_change > 30:

            alerts.append((
                "Distribution",
                old_avg,
                new_avg,
                f"Average order amount changed by {amount_change:.2f}%",
                "WARNING"
            ))

    # Freshness comparison
    latest_date = pd.to_datetime(
        profile["latest_date"]
    )

    age = (
        pd.Timestamp.now().normalize() -
        latest_date.normalize()
    ).days

    if age > 2:

        alerts.append((
            "Freshness",
            "Within 2 days",
            str(latest_date.date()),
            f"Latest data is {age} days old",
            "WARNING"
        ))

    # Save alerts in database
    for alert in alerts:

        cursor.execute("""
        INSERT INTO data_quality_alerts
        VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, *alert))

    conn.commit()

    if alerts:

        print("\nDATA QUALITY ALERTS")

        for alert in alerts:

            print("\nMetric:", alert[0])
            print("Severity:", alert[4])
            print("Reason:", alert[3])

    else:

        print("\nNo major data quality issues found.")


def run_pipeline(file_path, is_baseline=False):

    run_id = os.path.splitext(
        os.path.basename(file_path)
    )[0]

    print("\n==========================")
    print("Pipeline started:", run_id)
    print("==========================")

    # Remove previous results for same batch
    for table in [
        "pipeline_runs",
        "data_quality_alerts",
        "rejected_records",
        "orders"
    ]:

        cursor.execute(
            f"DELETE FROM {table} WHERE run_id = ?",
            (run_id,)
        )

    conn.commit()

    # Read dataset
    df = read_data(file_path)

    # Validate records
    valid_data, rejected_data = validate_data(df)

    print("Valid records:", len(valid_data))
    print("Rejected records:", len(rejected_data))

    # Save rejected records
    for _, row in rejected_data.iterrows():

        cursor.execute("""
        INSERT INTO rejected_records
        VALUES (?, ?, ?, ?)
        """, (
            run_id,
            file_path,
            row["order_id"]
            if pd.notna(row["order_id"])
            else None,
            row["rejection_reason"]
        ))

    # Save valid records
    for _, row in valid_data.iterrows():

        cursor.execute("""
        INSERT INTO orders
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(row["order_id"]),
            row["customer_id"],
            float(row["order_amount"]),
            row["city"],
            str(row["order_date"]),
            run_id
        ))

    # Create profile
    profile = create_profile(df)

    if is_baseline:

        save_baseline(profile)

    else:

        compare_data(profile, run_id)

    # Save pipeline status
    status = (
        "SUCCESS"
        if len(rejected_data) == 0
        else "COMPLETED_WITH_REJECTS"
    )

    cursor.execute("""
    INSERT OR REPLACE INTO pipeline_runs
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        file_path,
        len(df),
        len(valid_data),
        len(rejected_data),
        status
    ))

    conn.commit()

    print("\nPipeline status:", status)


def export_reports():

    reports = {

        "pipeline_summary.csv":
            "SELECT * FROM pipeline_runs",

        "quality_alerts.csv":
            "SELECT * FROM data_quality_alerts",

        "rejected_records.csv":
            "SELECT * FROM rejected_records",

        "baseline_profile.csv":
            "SELECT * FROM baseline_profiles"
    }

    for filename, query in reports.items():

        report = pd.read_sql_query(query, conn)

        report.to_csv(
            os.path.join("reports", filename),
            index=False
        )

        print(
            filename,
            "generated successfully!"
        )


if __name__ == "__main__":

    run_pipeline(
        "data/batch_001.csv",
        is_baseline=True
    )

    run_pipeline(
        "data/batch_002.csv",
        is_baseline=False
    )
    export_reports()

    print("\nProject execution completed!")

    conn.close()
