import sys, glob, os
import pandas as pd
out = open(sys.argv[2], "w", encoding="utf-8")
for p in sys.argv[1].split(";"):
    for f in sorted(glob.glob(p)):
        out.write(f"##### FILE {os.path.basename(f)}\n")
        try:
            sheets = pd.read_excel(f, sheet_name=None, header=None)
        except Exception as e:
            out.write(f"ERR {e}\n"); continue
        for name, df in sheets.items():
            out.write(f"=== {name} {df.shape}\n")
            for _, r in df.iterrows():
                vals = ["" if pd.isna(v) else str(v).replace("\n", " ") for v in r]
                if any(vals):
                    out.write(" | ".join(vals) + "\n")
out.close()
