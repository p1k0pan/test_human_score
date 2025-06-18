import pandas as pd
from pathlib import Path

folder = ["/mnt/data/users/liamding/data/MTI/evaluations/qwen-vl-max-2025-01-25/cluster_mit10m/de",
          "/mnt/data/users/liamding/data/MTI/evaluations/qwen-vl-max-2025-01-25/cluster_mit10m/en",
          "/mnt/data/users/liamding/data/MTI/evaluations/qwen-vl-max-2025-01-25/cluster_mit10m/zh"]
        
total = []
for f in folder:
    fa = Path(f)
    all = []
    for file in fa.glob("*each_fix.csv"):
        df = pd.read_csv(file)
        all.append(df)
    all_df = pd.concat(all, ignore_index=True)
    total.append(all_df)
total_df = pd.concat(total, ignore_index=True)
print(len(total_df))
total_df.to_csv(Path(fa.parent) / "all_each_fix.csv", index=False)