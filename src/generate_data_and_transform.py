import pandas as pd
import numpy as np
import sqlite3
import os

# -----------------------------
# 1️⃣ Generate raw transaction data
# -----------------------------

np.random.seed(42)

# Number of customers
n_customers = 200

# Create customer base with signup date
customers = pd.DataFrame({
    "customer_id": np.arange(1, n_customers + 1),
    "signup_date": pd.to_datetime("2020-01-01") + pd.to_timedelta(np.random.randint(0, 365, n_customers), unit="D")
})

# Add demographic features
customers["age"] = np.random.randint(18, 70, size=n_customers)
customers["income"] = np.random.normal(50000, 15000, size=n_customers).astype(int)
customers["gender"] = np.random.choice(["male", "female"], size=n_customers)
customers["education_level"] = np.random.choice(["high_school", "bachelor", "master", "phd"], size=n_customers)
customers["marital_status"] = np.random.choice(["single", "married", "divorced"], size=n_customers)
customers["profession"] = np.random.choice(["worker", "manager", "executive"], size=n_customers)
customers["household_size"] = np.random.randint(1, 6, size=n_customers)
customers["customer_segment"] = np.random.choice(["regular", "vip", "new"], size=n_customers)

# Generate individual transactions
transactions = []
for cid in customers["customer_id"]:
    n_tx = np.random.poisson(5)  # number of purchases per customer ~ Poisson
    for _ in range(n_tx):
        days_offset = np.random.randint(0, 730)  # within 2 years
        tx_date = customers.loc[customers.customer_id == cid, "signup_date"].values[0] + np.timedelta64(days_offset, 'D')
        amount = np.random.gamma(2, 50) + 5  # always > 0
        transactions.append([cid, tx_date, amount])

tx_df = pd.DataFrame(transactions, columns=["customer_id", "tx_date", "amount"])
tx_df = tx_df[tx_df["tx_date"] <= pd.to_datetime("2022-12-31")]

print("✅ Sample raw transaction data:")
print(tx_df.head())

# -----------------------------
# 2️⃣ Transform to RFM table for BG/NBD & GG models
# -----------------------------

# Define snapshot date for calculations
snapshot_date = tx_df["tx_date"].max()

rfm = (
    tx_df.groupby("customer_id").agg({
        "tx_date": [
            lambda x: (x.max() - x.min()).days,  # Recency: days between first and last transaction
            lambda x: (snapshot_date - x.min()).days,  # T: customer age since first transaction
            "count"
        ],
        "amount": "mean"
    })
)

rfm.columns = ["recency", "T", "frequency", "monetary_value"]

# Ensure frequency >= 1 for BG/NBD models
rfm["frequency"] = rfm["frequency"].clip(lower=1)
rfm["monetary_value"] = rfm["monetary_value"].round(2)

print("\n✅ Sample RFM data:")
print(rfm.head())


# -----------------------------
# Merge demographic features from customers
# -----------------------------

rfm = rfm.merge(customers.drop(columns=["signup_date"]), left_index=True, right_on="customer_id")

# One-hot encode categorical demographic variables
categorical_cols = ["gender", "education_level", "marital_status", "profession", "customer_segment"]
rfm = pd.get_dummies(rfm, columns=categorical_cols, drop_first=True)


# -----------------------------
# 3️⃣ Add churn & promotion flags for churn prediction + uplift modeling
# -----------------------------

rfm["promotion_offer"] = np.random.binomial(1, 0.5, len(rfm))  # uplift flag

# Get first & last transaction dates per customer
agg_dates = tx_df.groupby("customer_id").agg({
    "tx_date": ["min", "max"]
})
agg_dates.columns = ["first_tx_date", "last_tx_date"]

rfm = rfm.merge(agg_dates, left_on="customer_id", right_index=True)

# If no purchase in last 90 days => churned
rfm["days_since_last_tx"] = (snapshot_date - rfm["last_tx_date"]).dt.days

# Implicit churn flag (no purchase in last 90 days)
rfm["implicit_churn"] = (rfm["days_since_last_tx"] > 90).astype(int)

# Calculate churn probability based on demographic features
def demographic_churn_prob(row):
    base_prob = 0.1
    age_effect = 0.02 * (row['age'] - 30)  # age above 30: increases likelihood of churn
    income_effect = -0.00005 * (row['income'] - 40000)  # higher income: decreases likelihood of churn
    profession_effect = 0
    # assuming 'profession_Engineer' is a one-hot encoded variable; adjust if needed
    if row.get('profession_Engineer', 0) == 1:
        profession_effect = -0.15  # engineers are less likely to churn
    
    prob = base_prob + age_effect + income_effect + profession_effect
    
    # clip to ensure probability is between 0 and 1
    return min(max(prob, 0), 1)

rfm["demographic_churn_prob"] = rfm.apply(demographic_churn_prob, axis=1)

# Promotion reduces churn probability by 30% (relative)
def final_churn_prob(row):
    prob = row["demographic_churn_prob"]
    if row["promotion_offer"] == 1:
        prob = prob * 0.7  # promotion reduces churn by 30%
    return prob

rfm["final_churn_prob"] = rfm.apply(final_churn_prob, axis=1)

# Assign churned based on final churn prob (stochastic)
rfm["churned"] = rfm["final_churn_prob"].apply(lambda p: np.random.binomial(1, p))


# Duration: if churned -> last_tx - first_tx, else snapshot - first_tx
rfm["duration"] = np.where(
    rfm["churned"] == 1,
    (rfm["last_tx_date"] - rfm["first_tx_date"]).dt.days,
    (snapshot_date - rfm["first_tx_date"]).dt.days
)

# Clean up
rfm = rfm.drop(columns=["first_tx_date", "last_tx_date", "days_since_last_tx"])

print("\n✅ Duration & churn added with business rule")
print(rfm.head())



# -----------------------------
# ✅ Add more covariates
# -----------------------------

# Tenure group: group customer lifetime
rfm["tenure_group"] = pd.cut(
    rfm["T"], 
    bins=[0, 180, 365, 730, 10000],
    labels=["<6m", "6-12m", "1-2y", ">2y"]
)

# High value flag: spending above median
rfm["high_value_flag"] = (rfm["monetary_value"] > rfm["monetary_value"].median()).astype(int)

# Purchase trend: did purchase frequency drop in last 6 months?
six_months_ago = snapshot_date - pd.DateOffset(months=6)
tx_last6 = tx_df[tx_df["tx_date"] >= six_months_ago].groupby("customer_id")["amount"].count()
tx_before6 = tx_df[tx_df["tx_date"] < six_months_ago].groupby("customer_id")["amount"].count()
tx_trend = (tx_last6 / tx_before6).fillna(0)
rfm["purchase_trend"] = tx_trend.reindex(rfm.index).fillna(0)

# Seasonal user: buys more in summer than winter
tx_df["month"] = tx_df["tx_date"].dt.month
summer = tx_df[tx_df["month"].isin([6, 7, 8])].groupby("customer_id").size()
winter = tx_df[tx_df["month"].isin([12, 1, 2])].groupby("customer_id").size()

# Ensure same index
summer = summer.reindex(rfm.index).fillna(0)
winter = winter.reindex(rfm.index).fillna(0)

rfm["seasonal_user"] = (summer > winter).reindex(rfm.index).fillna(False).astype(int)

# Number of active months
tx_df["year_month"] = tx_df["tx_date"].dt.to_period("M").astype(str)
active_months = tx_df.groupby("customer_id")["year_month"].nunique()
rfm["num_active_months"] = active_months.reindex(rfm.index).fillna(0)

# Average days between transactions
avg_days = (
    tx_df.sort_values(["customer_id", "tx_date"])
    .groupby("customer_id")["tx_date"]
    .apply(lambda x: x.diff().dt.days.mean())
)
rfm["avg_days_between_tx"] = avg_days.reindex(rfm.index).fillna(rfm["T"])

# One-hot encode tenure_group for causal modeling
tenure_dummies = pd.get_dummies(rfm["tenure_group"], prefix="tenure")
rfm = pd.concat([rfm, tenure_dummies], axis=1)
rfm = rfm.drop(columns=["tenure_group"])

print("\n✅ Added more covariates:")
print(rfm.head())


# -----------------------------
# 4️⃣ Save to SQLite
# -----------------------------

os.makedirs("data", exist_ok=True)
with sqlite3.connect("bank.db") as conn:
    tx_df.to_sql("raw_transactions", conn, if_exists="replace", index=False)
    rfm.to_sql("customer_data", conn, if_exists="replace", index=False)

print("\n✅ Data generated and saved to `data/bank.db`")
print(" - `raw_transactions` (raw transactional data)")
print(" - `customer_data` (RFM + churn + promo flags)")
