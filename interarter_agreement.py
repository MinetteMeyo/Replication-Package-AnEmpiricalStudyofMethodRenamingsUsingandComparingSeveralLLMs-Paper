import re
import pandas as pd
import krippendorff

CSV_FILE = "Responses.csv"
CANDIDATES_PER_METHOD = 6
GOOD_BAD_MAP = {1: 1, 2: 1, 5: 2, 6: 2}  # Good -> 1, Bad -> 2

df = pd.read_csv(CSV_FILE)
good_bad = df.replace(GOOD_BAD_MAP)

n_raters, n_cols = df.shape
n_methods = n_cols // CANDIDATES_PER_METHOD
print(f"{n_raters} raters, {n_methods} methods\n")

# ---- Primary analysis: raw ordinal scale ----
overall_raw = krippendorff.alpha(reliability_data=df.to_numpy(dtype=float),
                                  level_of_measurement="ordinal")
print("PRIMARY ANALYSIS (raw ordinal scale)")
print(f"Overall alpha: {overall_raw:.4f}\n")

print(f"{'method':<12s}{'alpha':>8s}")
counts = {}
for i in range(n_methods):
    cols = df.columns[i * CANDIDATES_PER_METHOD:(i + 1) * CANDIDATES_PER_METHOD]
    language = re.sub(r'\d+$', '', cols[0].split("()")[0].strip())
    counts[language] = counts.get(language, 0) + 1
    method_name = f"{language}{counts[language]}"

    a = krippendorff.alpha(reliability_data=df[cols].to_numpy(dtype=float),
                            level_of_measurement="ordinal")
    print(f"{method_name:<12s}{a:>8.4f}")

# ---- Secondary analysis: collapsed Good/Bad ----
overall_gb = krippendorff.alpha(reliability_data=good_bad.to_numpy(dtype=float),
                                 level_of_measurement="nominal")
print("\nSECONDARY ANALYSIS (Good/Bad, nominal)")
print(f"Overall alpha: {overall_gb:.4f}\n")

print(f"{'method':<12s}{'alpha':>8s}")
counts = {}
for i in range(n_methods):
    cols = df.columns[i * CANDIDATES_PER_METHOD:(i + 1) * CANDIDATES_PER_METHOD]
    language = re.sub(r'\d+$', '', cols[0].split("()")[0].strip())
    counts[language] = counts.get(language, 0) + 1
    method_name = f"{language}{counts[language]}"

    a = krippendorff.alpha(reliability_data=good_bad[cols].to_numpy(dtype=float),
                            level_of_measurement="nominal")
    print(f"{method_name:<12s}{a:>8.4f}")
