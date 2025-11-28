import pandas as pd

# Load train data
df = pd.read_parquet('../data-pipeline/datasets/processed/training_data.parquet')

print("Columns:")
for col in df.columns:
    print(f"- {col}")

print("\nFirst row:")
print(df.iloc[0])
