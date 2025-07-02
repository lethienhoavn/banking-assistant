import sqlite3
from pydantic.v1 import BaseModel
from typing import List, Dict, Any
from langchain.tools import Tool
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifelines import CoxPHFitter
from sklearn.ensemble import RandomForestClassifier
from sklift.models import ClassTransformation
import pandas as pd
from causalnex.structure.notears import from_pandas
from sklearn.preprocessing import StandardScaler

# SQLite connection
conn = sqlite3.connect("bank.db")

# Schema for tools with top K argument
class TopKArgsSchema(BaseModel):
    k: int

# ---------- Calculate CLV: Top K customers for upsell ----------
def calculate_clv_top_k(k: int) -> List[Dict[str, Any]]:
    df = pd.read_sql_query("SELECT * FROM customer_data", conn)

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    ggf = GammaGammaFitter(penalizer_coef=0.01)

    df['T_months'] = df['T'] / 30
    df['recency_months'] = df['recency'] / 30

    bgf.fit(df['frequency'], df['recency_months'], df['T_months'])
    ggf.fit(df['frequency'], df['monetary_value'])

    clv = ggf.customer_lifetime_value(
        bgf,
        df['frequency'],
        df['recency_months'],
        df['T_months'],
        df['monetary_value'],
        time=12
    )

    df['clv'] = clv

    top_k = df[['customer_id', 'clv']].sort_values(by='clv', ascending=False).head(k)

    return top_k.to_dict(orient='records')

calculate_clv_tool = Tool.from_function(
    name="calculate_clv_top_k",
    description="Calculate Customer Lifetime Value (CLV) and get top K customers for upsell.",
    func=calculate_clv_top_k,
    args_schema=TopKArgsSchema
)



# ---------- Survival Analysis: Time to churn for top K risky customers ----------
def survival_analysis_top_k(k: int) -> List[Dict[str, Any]]:
    df = pd.read_sql_query("SELECT * FROM customer_data", conn)

    covariates = [
        "recency", "frequency", "monetary_value", "promotion_offer",
        "high_value_flag", "purchase_trend", "seasonal_user",
        "num_active_months", "avg_days_between_tx"
    ]
    covariates += [col for col in df.columns if col.startswith("tenure_")]

    cph = CoxPHFitter()
    cph.fit(df[["duration", "churned"] + covariates], duration_col="duration", event_col="churned")

    expected_survival = cph.predict_expectation(df[covariates])
    df["expected_survival"] = expected_survival
    df["days_remaining_to_churn"] = (
        df["expected_survival"] - df["duration"]
    ).where(df["churned"] == 0, 0).clip(lower=0)

    # Customers with shortest days remaining are highest churn risk
    top_k = df[['customer_id', 'days_remaining_to_churn']].sort_values(
        by='days_remaining_to_churn'
    ).head(k)

    return top_k.to_dict(orient='records')

survival_analysis_tool = Tool.from_function(
    name="survival_analysis_top_k",
    description="Estimate remaining time to churn for top K highest-risk customers.",
    func=survival_analysis_top_k,
    args_schema=TopKArgsSchema
)



# ---------- Churn Classification: Top K customers with highest churn probability ----------
def churn_classification_top_k(k: int) -> List[Dict[str, Any]]:
    df = pd.read_sql_query("SELECT * FROM customer_data", conn)

    X = df.drop(columns=['churned'])
    y = df['churned']

    clf = RandomForestClassifier()
    clf.fit(X, y)

    churn_probs = clf.predict_proba(X)[:, 1]
    df['churn_prob'] = churn_probs

    top_k = df[['customer_id', 'churn_prob']].sort_values(by='churn_prob', ascending=False).head(k)

    return top_k.to_dict(orient='records')

churn_classification_tool = Tool.from_function(
    name="churn_classification_top_k",
    description="Predict churn probability and get top K customers with highest churn risk.",
    func=churn_classification_top_k,
    args_schema=TopKArgsSchema
)



# ---------- Uplift Modeling: Count customers with positive uplift ----------
def uplift_modeling_positive() -> Dict[str, Any]:
    df = pd.read_sql_query("SELECT * FROM customer_data", conn)

    X = df.drop(columns=['churned'])
    y = df['churned']

    uplift_model = ClassTransformation(RandomForestClassifier())
    uplift_model.fit(X, y, treatment=X['promotion_offer'])
    uplift = uplift_model.predict(X)

    df['uplift'] = uplift

    num_positive_uplift = (df['uplift'] > 0).sum()

    return {"num_customers_positive_uplift": int(num_positive_uplift)}

uplift_modeling_tool = Tool.from_function(
    name="uplift_modeling_positive",
    description="Count how many customers have positive uplift if given a promotion.",
    func=uplift_modeling_positive,
    args_schema=BaseModel  # No args needed
)



# ---------- Discover potential causal factors for churn ----------
def discover_churn_factors() -> Dict[str, Any]:
    df = pd.read_sql_query("SELECT * FROM customer_data", conn)

    demographic_cols = [
        "age", "income", "household_size",
    ] + [col for col in df.columns if col.startswith((
        "gender_", "education_level_", "marital_status_", 
        "profession_", "customer_segment_"
    ))]

    demographic_cols = [c for c in demographic_cols if c in df.columns]
    cols_to_use = demographic_cols + ["churned"]

    data = df[cols_to_use].copy()
    data = data.apply(pd.to_numeric, errors='coerce').dropna()

    scaler = StandardScaler()
    features = [c for c in data.columns if c != "churned"]
    data_scaled = pd.DataFrame(scaler.fit_transform(data[features]), columns=features, index=data.index)
    data_scaled["churned"] = data["churned"]

    sm = from_pandas(data_scaled, max_iter=2000)

    causal_factors = []
    for u, v, w in sm.edges(data=True):
        if v == "churned" and abs(w['weight']) > 0.01:
            causal_factors.append({
                "feature": u,
                "weight": round(w['weight'], 4)
            })

    return {"churn_factors": causal_factors}

discover_churn_factors_tool = Tool.from_function(
    name="discover_churn_factors",
    description="Discover factors that may causally influence churn.",
    func=discover_churn_factors,
    args_schema=BaseModel  # No args needed
)