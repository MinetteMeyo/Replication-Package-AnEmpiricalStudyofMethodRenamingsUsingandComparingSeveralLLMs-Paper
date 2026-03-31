import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare
import scikit_posthocs as sp

filename = './raw_method_data.csv'
df = pd.read_csv(filename)

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

n_methods = data.shape[0]
k_participants = data.shape[1]
kendall_w = stat / (n_methods * (k_participants - 1))

if kendall_w < 0.1:
    interpretation = "weak"
elif kendall_w < 0.3:
    interpretation = "moderate"
else:
    interpretation = "strong"
  
if proceed_posthoc:
    
    df_test = pd.DataFrame(data, columns=participants)
    posthoc = sp.posthoc_nemenyi_friedman(df_test)
    
    llms = [c for c in participants if 'Claude' in c or 'GPT' in c or 'Llama' in c]
    humans = [c for c in participants if 'developer' in c]
    original = [c for c in participants if 'original' in c]
  
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
