import pandas as pd

try:
    df = pd.read_csv('method_names_coded1.csv')
except FileNotFoundError:
    exit()

def classify_quality(row):
    if row['good_count'] >= 6:
        return 'High'
    elif row['bad_count'] >= 4:
        return 'Low'
    else:
        return 'Medium'

df['quality'] = df.apply(classify_quality, axis=1)

# Filter to LLMs only
df_llms = df[df['llm'].isin(['Claude', 'GPT-5', 'Llama'])].copy()

high_quality = df_llms[df_llms['quality'] == 'High']
low_quality = df_llms[df_llms['quality'] == 'Low']
medium_quality = df_llms[df_llms['quality'] == 'Medium']

# Overall quality
print(f"{'Overall quality':30s} {'High-quality':25s} {len(high_quality):>10d}")
print(f"{'':30s} {'Low-quality':25s} {len(low_quality):>10d}")

print()

# High-quality per LLM
print(f"{'High-quality per LLM':30s} {'Claude Sonnet 4.5':25s} {len(high_quality[high_quality['llm']=='Claude']):>10d}")
print(f"{'':30s} {'GPT-5':25s} {len(high_quality[high_quality['llm']=='GPT-5']):>10d}")
print(f"{'':30s} {'Llama-4':25s} {len(high_quality[high_quality['llm']=='Llama']):>10d}")

print()

# Low-quality per LLM
print(f"{'Low-quality per LLM':30s} {'Claude Sonnet 4.5':25s} {len(low_quality[low_quality['llm']=='Claude']):>10d}")
print(f"{'':30s} {'GPT-5':25s} {len(low_quality[low_quality['llm']=='GPT-5']):>10d}")
print(f"{'':30s} {'Llama-4':25s} {len(low_quality[low_quality['llm']=='Llama']):>10d}")

print()

# High-quality per language
print(f"{'High-quality per language':30s} {'Java':25s} {len(high_quality[high_quality['language']=='Java']):>10d}")
print(f"{'':30s} {'Python':25s} {len(high_quality[high_quality['language']=='Python']):>10d}")
print(f"{'':30s} {'JavaScript':25s} {len(high_quality[high_quality['language']=='JavaScript']):>10d}")

print(f"\n{'Method name':35s} {'Lang':12s} {'LLM':8s} {'Quality':10s} {'Score':8s} {'Words':8s}")

print("HIGH-QUALITY EXAMPLES")

# Get high-quality examples
high_examples = []
for llm in ['Claude', 'GPT-5', 'Llama']:
    llm_high = high_quality[high_quality['llm'] == llm]
    if len(llm_high) > 0:
        best = llm_high.nlargest(2, 'good_count')
        for idx in range(min(2, len(best))):
            high_examples.append(best.iloc[idx])

for row in high_examples[:6]:
    print(f"{row['actual_name']:35s} {row['language']:12s} {row['llm']:8s} {'High':10s} {row['good_count']:2d}/9{'':<4s} {row['word_count']:8d}")

if len(low_quality) > 0:
    for idx, row in low_quality.iterrows():
        print(f"{row['actual_name']:35s} {row['language']:12s} {row['llm']:8s} {'Low':10s} {row['bad_count']:2d}/9{'':<4s} {row['word_count']:8d}")
else:
    print("No low-quality names found")

# Calculate statistics
high_wc_mean = high_quality['word_count'].mean()
high_wc_median = high_quality['word_count'].median()
high_wc_min = high_quality['word_count'].min()
high_wc_max = high_quality['word_count'].max()

high_has_verb = (high_quality['has_verb'] == 'Yes').sum()
high_has_verb_pct = (high_has_verb / len(high_quality)) * 100

high_with_verbs = high_quality[high_quality['has_verb'] == 'Yes']
if len(high_with_verbs) > 0:
    high_specific = (high_with_verbs['verb_specificity'] == 'Specific').sum()
    high_specific_pct = (high_specific / len(high_with_verbs)) * 100
else:
    high_specific = 0
    high_specific_pct = 0

high_conv = (high_quality['follows_convention'] == 'Yes').sum()
high_conv_pct = (high_conv / len(high_quality)) * 100

# Low-quality statistics
if len(low_quality) > 0:
    low_wc_mean = low_quality['word_count'].mean()
    low_wc_median = low_quality['word_count'].median()
    low_wc_min = low_quality['word_count'].min()
    low_wc_max = low_quality['word_count'].max()
    
    low_has_verb = (low_quality['has_verb'] == 'Yes').sum()
    low_has_verb_pct = (low_has_verb / len(low_quality)) * 100
    
    low_with_verbs = low_quality[low_quality['has_verb'] == 'Yes']
    if len(low_with_verbs) > 0:
        low_specific = (low_with_verbs['verb_specificity'] == 'Specific').sum()
        low_specific_pct = (low_specific / len(low_with_verbs)) * 100
    else:
        low_specific = 0
        low_specific_pct = 0
    
    low_conv = (low_quality['follows_convention'] == 'Yes').sum()
    low_conv_pct = (low_conv / len(low_quality)) * 100
else:
    low_wc_mean = low_wc_median = low_wc_min = low_wc_max = 0
    low_has_verb = low_has_verb_pct = 0
    low_specific = low_specific_pct = 0
    low_conv = low_conv_pct = 0



print(f"\n{'Pattern':30s} {'High-quality (n=' + str(len(high_quality)) + ')':30s} {'Low-quality (n=' + str(len(low_quality)) + ')':30s}")
print("-"*95)

print(f"{'Mean word count':30s} {high_wc_mean:30.2f} {low_wc_mean:30.2f}")
print(f"{'Median word count':30s} {high_wc_median:30.1f} {low_wc_median:30.1f}")
print(f"{'Word count range':30s} {str(high_wc_min) + '-' + str(high_wc_max):30s} {str(low_wc_min) + '-' + str(low_wc_max):30s}")
print(f"{'Contains a verb':30s} {f'{high_has_verb}/{len(high_quality)} ({high_has_verb_pct:.1f}%)':30s} {f'{low_has_verb}/{len(low_quality)} ({low_has_verb_pct:.1f}%)':30s}")

if len(high_with_verbs) > 0 and len(low_with_verbs) > 0:
    print(f"{'Specific verb usage':30s} {f'{high_specific}/{len(high_with_verbs)} ({high_specific_pct:.1f}%)':30s} {f'{low_specific}/{len(low_with_verbs)} ({low_specific_pct:.1f}%)':30s}")
else:
    print(f"{'Specific verb usage':30s} {f'{high_specific}/{len(high_with_verbs)} ({high_specific_pct:.1f}%)' if len(high_with_verbs) > 0 else 'N/A':30s} {'N/A':30s}")

print(f"{'Convention adherence':30s} {f'{high_conv}/{len(high_quality)} ({high_conv_pct:.1f}%)':30s} {f'{low_conv}/{len(low_quality)} ({low_conv_pct:.1f}%)':30s}")
