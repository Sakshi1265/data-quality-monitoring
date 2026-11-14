
import pandas as pd
import numpy as np
import os

os.makedirs("data", exist_ok=True)

np.random.seed(42)

batch1 = pd.DataFrame({
    "order_id": range(1, 101),
    "customer_id": ["C" + str(i) for i in range(1, 101)],
    "order_amount": np.random.randint(500, 3000, 100),
    "city": np.random.choice(
        ["Pune", "Delhi", "Mumbai"], 100
    ),
    "order_date": np.random.choice(
        pd.date_range("2026-11-10", "2026-11-14"), 100
    )
})

batch2 = pd.DataFrame({
    "order_id": range(101, 151),
    "customer_id": ["C" + str(i) for i in range(101, 151)],
    "order_amount": np.random.randint(2000, 6000, 50),
    "city": np.random.choice(
        ["Pune", "Delhi", "Mumbai"], 50
    ),
    "order_date": np.random.choice(
        pd.date_range("2026-11-01", "2026-11-05"), 50
    )
})

# Add missing values
batch2.loc[0:14, "customer_id"] = None

# Add duplicate order ID
batch2.loc[20, "order_id"] = 101

# Add negative amount
batch2.loc[30, "order_amount"] = -500

# Save CSV files
batch1.to_csv("data/batch_001.csv", index=False)
batch2.to_csv("data/batch_002.csv", index=False)

print("Both datasets generated successfully!")
