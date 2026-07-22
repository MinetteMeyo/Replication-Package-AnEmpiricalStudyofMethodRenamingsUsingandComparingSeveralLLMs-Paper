import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare
import scikit_posthocs as sp

# ============================================================
# LOAD DATA
# ============================================================
filename = '/home/minette/0_XP_Refactoring/Code-naming/raw_method_data.csv'
df = pd.read_csv(filename)

print("✓ Data loaded successfully!\n")

# ============================================================
# BUILD DATA MATRIX
# ============================================================
participants = df['Category'].unique()
method_ids = df['Method_id'].unique()

data_matrix = []
for method_id in method_ids:
    method_scores = []
    for participant in participants:
        row = df[(df['Method_id'] == method_id) & (df['Category'] == participant)]
        good = int(row['Good'].values[0])
        score = good / 9  # Proportion of Good rankings
        method_scores.append(score)
    data_matrix.append(method_scores)

data = np.array(data_matrix)

# ============================================================
# FRIEDMAN TEST
# ============================================================
print("="*70)
print("FRIEDMAN TEST (based on Good rankings only)")
print("="*70)

stat, p_value = friedmanchisquare(*data.T)

print(f"\n  Chi-square statistic (χ²): {stat:.2f}")
print(f"  Degrees of freedom (df): {len(participants)-1}")
print(f"  P-value: {p_value:.6f}")

print(f"\nDecision:")
if p_value < 0.05:
    print(f"  ✓ REJECT H₀ (p = {p_value:.6f} < 0.05)")
    print(f"  ✓ Significant differences exist among participants")
    proceed_posthoc = True
else:
    print(f"  ✗ FAIL TO REJECT H₀ (p = {p_value:.6f} ≥ 0.05)")
    print(f"  ✗ No significant differences detected")
    proceed_posthoc = False

# ============================================================
# EFFECT SIZE (Kendall's W)
# ============================================================
print("\n" + "-"*70)
print("EFFECT SIZE (Kendall's W)")
print("-"*70)

n_methods = data.shape[0]
k_participants = data.shape[1]
kendall_w = stat / (n_methods * (k_participants - 1))

print(f"\nKendall's W: {kendall_w:.3f}")
print(f"  (Range: 0 = no agreement, 1 = perfect agreement)")

if kendall_w < 0.1:
    interpretation = "weak"
elif kendall_w < 0.3:
    interpretation = "moderate"
else:
    interpretation = "strong"
    
print(f"  Interpretation: {interpretation} effect")

# ============================================================
# NEMENYI POST-HOC
# ============================================================
if proceed_posthoc:
    print("\n" + "="*70)
    print("NEMENYI POST-HOC TEST - COMPLETE MATRIX")
    print("="*70)
    
    df_test = pd.DataFrame(data, columns=participants)
    posthoc = sp.posthoc_nemenyi_friedman(df_test)
    
    print("\nComplete pairwise p-values:")
    print(posthoc.round(4))
    
    llms = [c for c in participants if 'Claude' in c or 'GPT' in c or 'Llama' in c]
    humans = [c for c in participants if 'developer' in c]
    original = [c for c in participants if 'original' in c]
    
    print("\n" + "="*70)
    print("SIGNIFICANT COMPARISONS (p < 0.05)")
    print("="*70)
    
    print("\nLLMs vs Humans:")
    for llm in llms:
        for human in humans:
            p = posthoc.loc[llm, human]
            sig = "✓ SIG" if p < 0.05 else "✗ n.s."
            print(f"  {sig} {llm:30s} vs {human:30s}: p = {p:.4f}")
    
    print("\nLLMs vs Original:")
    for llm in llms:
        for orig in original:
            p = posthoc.loc[llm, orig]
            sig = "✓ SIG" if p < 0.05 else "✗ n.s."
            print(f"  {sig} {llm:30s} vs {orig:30s}: p = {p:.4f}")
else:
    print("\n⚠ Post-hoc test skipped (Friedman test not significant)")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*70)
print("SUMMARY (Good rankings only)")
print("="*70)

summary = df.groupby('Category')[['Good', 'Avg', 'Bad']].sum()
summary['Total'] = summary['Good'] + summary['Avg'] + summary['Bad']
summary['Good %'] = (summary['Good'] / summary['Total'] * 100).round(1)

for participant in participants:
    good = summary.loc[participant, 'Good']
    total = summary.loc[participant, 'Total']
    pct = summary.loc[participant, 'Good %']
    print(f"{participant:30s}: {good:3.0f}/{total:.0f} ({pct:5.1f}% Good)")

print("="*70)
