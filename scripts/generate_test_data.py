"""
Run this once to fill the data/ folder with realistic test datasets.

    python scripts/generate_test_data.py

Generates 5 CSVs, each designed to test a different quality scenario:
  employees.csv        — 500 rows, moderate quality (real-world feel)
  sales.csv            — 300 rows, messy amounts & some nulls
  medical.csv          — 200 rows, high null rate (typical for sensitive data)
  clean_benchmark.csv  — 100 rows, near-perfect (use as a quality baseline)
  messy_benchmark.csv  — 100 rows, intentionally terrible (use to stress-test)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DEPARTMENTS = ["Engineering", "HR", "Finance", "Marketing", "Sales", "Operations"]
CITIES = ["New York", "Seattle", "Austin", "Chicago", "Boston", "Denver", "Portland", "Miami", "San Francisco", "Phoenix"]
REGIONS = ["North", "South", "East", "West", "Central"]
PRODUCTS = ["Widget A", "Widget B", "Gadget Pro", "Starter Kit", "Premium Bundle", "Basic Plan", "Enterprise Plan"]
CATEGORIES = ["Electronics", "Software", "Hardware", "Services", "Accessories"]
DIAGNOSES = ["Healthy", "Hypertension", "Diabetes", "Obesity", "Heart Disease"]


def _random_dates(n: int, start="2020-01-01", span_days=1460) -> list:
    base = datetime.strptime(start, "%Y-%m-%d")
    return [(base + timedelta(days=int(d))).strftime("%Y-%m-%d")
            for d in RNG.integers(0, span_days, n)]


def _inject_nulls(df: pd.DataFrame, columns: list, rate: float) -> pd.DataFrame:
    n = len(df)
    for col in columns:
        idx = RNG.choice(n, max(1, int(n * rate)), replace=False)
        df.loc[idx, col] = np.nan
    return df


# ── 1. Employees (500 rows, ~5% nulls, a few age/salary outliers) ─────────────
def generate_employees(n: int = 500) -> pd.DataFrame:
    ages = RNG.integers(22, 65, n).astype(float)
    ages[RNG.choice(n, 4, replace=False)] = [160, 200, -3, 0]   # bad ages

    salaries = (ages.clip(22, 65) * 1800 + RNG.normal(0, 8000, n)).clip(30000, 180000)
    salaries[RNG.choice(n, 2, replace=False)] = [500000, 1]      # extreme outliers

    df = pd.DataFrame({
        "employee_id":       range(1, n + 1),
        "name":              [f"Employee {i}" for i in range(1, n + 1)],
        "age":               ages,
        "department":        RNG.choice(DEPARTMENTS, n),
        "salary":            salaries.round(2),
        "experience_years":  (ages.clip(22,65) - 22 + RNG.normal(0, 2, n)).clip(0, 40).round(1),
        "performance_score": RNG.normal(84, 8, n).clip(0, 100).round(1),
        "city":              RNG.choice(CITIES, n),
        "hire_date":         _random_dates(n),
        "is_remote":         RNG.choice([True, False], n),
    })

    return _inject_nulls(df, ["age", "salary", "performance_score", "city", "hire_date"], 0.05)


# ── 2. Sales (300 rows, ~8% nulls, negative & extreme amounts) ────────────────
def generate_sales(n: int = 300) -> pd.DataFrame:
    amounts = RNG.exponential(150, n).round(2)
    amounts[RNG.choice(n, 5, replace=False)] = [-50, -120, 9999, 15000, 0]  # bad values

    df = pd.DataFrame({
        "transaction_id": range(1001, 1001 + n),
        "product":        RNG.choice(PRODUCTS, n),
        "category":       RNG.choice(CATEGORIES, n),
        "amount":         amounts,
        "quantity":       RNG.integers(1, 50, n).astype(float),
        "discount_pct":   RNG.uniform(0, 0.4, n).round(3),
        "region":         RNG.choice(REGIONS, n),
        "sale_date":      _random_dates(n, "2022-01-01", 730),
        "customer_id":    RNG.integers(100, 999, n).astype(float),
        "rep_id":         RNG.integers(10, 50, n),
    })

    return _inject_nulls(df, ["product", "amount", "region", "customer_id"], 0.08)


# ── 3. Medical (200 rows, ~15% nulls — typical for patient records) ───────────
def generate_medical(n: int = 200) -> pd.DataFrame:
    bp_sys = RNG.normal(125, 20, n).clip(70, 220)
    bp_sys[RNG.choice(n, 3, replace=False)] = [290, 310, 8]   # impossible BP readings
    bmi = RNG.normal(26, 5, n).clip(14, 55)
    bmi[RNG.choice(n, 2, replace=False)] = [95, 112]           # extreme BMI

    glucose = RNG.normal(100, 25, n).clip(50, 400)

    df = pd.DataFrame({
        "patient_id":    range(2001, 2001 + n),
        "age":           RNG.integers(18, 85, n).astype(float),
        "bp_systolic":   bp_sys.round(1),
        "bp_diastolic":  RNG.normal(80, 12, n).clip(40, 130).round(1),
        "cholesterol":   RNG.normal(200, 40, n).clip(100, 350).round(1),
        "glucose":       glucose.round(1),
        "bmi":           bmi.round(2),
        "diagnosis":     RNG.choice(DIAGNOSES + [None], n, p=[0.35, 0.2, 0.15, 0.1, 0.1, 0.1]),
        "is_diabetic":   (glucose > 126).astype(float),
    })

    return _inject_nulls(df, ["age", "cholesterol", "glucose", "bmi", "diagnosis", "bp_diastolic"], 0.15)


# ── 4. Clean benchmark (100 rows, <1% nulls, no outliers) ────────────────────
def generate_clean(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame({
        "id":       range(1, n + 1),
        "value_a":  RNG.normal(100, 5, n).round(2),
        "value_b":  RNG.normal(50, 3, n).round(2),
        "value_c":  RNG.integers(1, 10, n),
        "category": RNG.choice(["A", "B", "C"], n),
        "score":    RNG.uniform(0.7, 1.0, n).round(4),
        "flag":     RNG.choice([True, False], n),
    })


# ── 5. Messy benchmark (100 rows, ~40% nulls, extreme outliers) ──────────────
def generate_messy(n: int = 100) -> pd.DataFrame:
    df = pd.DataFrame({
        "id":       range(1, n + 1),
        "value_a":  RNG.normal(100, 5, n).round(2),
        "value_b":  RNG.normal(50, 3, n).round(2),
        "value_c":  RNG.integers(1, 10, n).astype(float),
        "category": RNG.choice(["A", "B", "C", None], n, p=[0.2, 0.2, 0.2, 0.4]),
        "score":    RNG.uniform(0, 1, n).round(4),
    })

    # 40% nulls in numeric columns
    for col in ["value_a", "value_b", "value_c", "score"]:
        idx = RNG.choice(n, 40, replace=False)
        df.loc[idx, col] = np.nan

    # Extreme outliers
    df.loc[RNG.choice(n, 10, replace=False), "value_a"] = RNG.choice([99999, -99999], 10)
    df.loc[RNG.choice(n, 10, replace=False), "value_b"] = RNG.choice([99999, -99999], 10)

    return df


def main() -> None:
    datasets = [
        ("employees.csv",       generate_employees(), "500 rows · employee records · ~5% nulls · salary/age outliers"),
        ("sales.csv",           generate_sales(),     "300 rows · sales transactions · ~8% nulls · bad amounts"),
        ("medical.csv",         generate_medical(),   "200 rows · patient data · ~15% nulls · extreme vitals"),
        ("clean_benchmark.csv", generate_clean(),     "100 rows · near-perfect quality · use as baseline"),
        ("messy_benchmark.csv", generate_messy(),     "100 rows · intentionally broken · stress-test the tool"),
    ]

    print("Generating test datasets...\n")
    for filename, df, description in datasets:
        path = DATA_DIR / filename
        df.to_csv(path, index=False)
        null_pct = round(df.isnull().mean().mean() * 100, 1)
        print(f"  {filename:<25} {len(df):>4} rows   {null_pct:>5}% nulls   {description.split('·')[-1].strip()}")

    print(f"\nAll files saved to: {DATA_DIR.resolve()}")
    print("Run the app and visit /api/v1/local-datasets to analyze them.")


if __name__ == "__main__":
    main()
