import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

# ============================================================
# LOAD DATA
# ============================================================
filename = '/home/minette/0_XP_Refactoring/Code-naming/raw_method_data.csv'
df = pd.read_csv(filename)

print("✓ Data loaded successfully!\n")

# ============================================================
# RQ3: DOES EACH LLM'S PERFORMANCE VARY ACROSS LANGUAGES?
# ============================================================
print("="*70)
print("RQ3: How does LLM performance vary across programming languages?")
print("="*70)
print("\nMethod: Chi-Square Test of Independence")
print("Separate test for each LLM across Java, Python, JavaScript")
print("="*70)

llms = ['Claude Sonnet 4.5', 'GPT 5', 'Llama 4']
languages = ['Java', 'Python', 'JavaScript']

results = []

for llm in llms:
    print(f"\n{'='*70}")
    print(f"LLM: {llm}")
    print(f"{'='*70}")
    
    # Build contingency table: Languages × Ratings
    llm_data = df[df['Category'] == llm]
    
    contingency_table = []
    for lang in languages:
        lang_data = llm_data[llm_data['Language'] == lang]
        good = lang_data['Good'].sum()
        avg = lang_data['Avg'].sum()
        bad = lang_data['Bad'].sum()
        contingency_table.append([good, avg, bad])
    
    contingency_table = np.array(contingency_table)
    
    # Display table
    print("\nContingency Table (Languages × Ratings):")
    df_table = pd.DataFrame(
        contingency_table,
        index=languages,
        columns=['Good', 'Avg', 'Bad']
    )
    df_table['Total'] = df_table.sum(axis=1)
    totals = df_table.sum(axis=0)
    df_table.loc['Total'] = totals
    print(df_table)
    
    # Chi-square test
    chi2, p_value, dof, expected = chi2_contingency(contingency_table)
    
    # Effect size (Cramér's V)
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
    cramers_v = np.sqrt(chi2 / (n * min_dim))
    
    print(f"\nTest Results:")
    print(f"  χ² = {chi2:.4f}")
    print(f"  df = {dof}")
    print(f"  p-value = {p_value:.6f}")
    print(f"  Cramér's V = {cramers_v:.3f}")
    
    # Interpretation
    if p_value < 0.05:
        conclusion = f"✓ SIGNIFICANT: {llm}'s performance varies across languages"
        print(f"\n{conclusion}")
        
        if cramers_v < 0.1:
            effect = "negligible"
        elif cramers_v < 0.3:
            effect = "small"
        elif cramers_v < 0.5:
            effect = "medium"
        else:
            effect = "large"
        print(f"  Effect size: {effect}")
    else:
        conclusion = f"✗ NOT SIGNIFICANT: {llm}'s performance is consistent across languages"
        print(f"\n{conclusion}")
    
    results.append({
        'LLM': llm,
        'χ²': chi2,
        'df': dof,
        'p-value': p_value,
        "Cramér's V": cramers_v,
        'Significant': p_value < 0.05
    })

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

print("\nConclusion:")
sig_llms = [r['LLM'] for r in results if r['Significant']]
if sig_llms:
    print(f"  LLMs with language-dependent performance: {', '.join(sig_llms)}")
else:
    print(f"  All LLMs perform consistently across languages")

print("="*70)
