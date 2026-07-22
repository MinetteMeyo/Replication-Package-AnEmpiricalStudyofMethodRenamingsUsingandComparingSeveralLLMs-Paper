import pandas as pd

print("="*70)
print("RQ4: What naming characteristics distinguish high-quality")
print("     LLM-generated method names?")
print("="*70)

# ===============================
# LOAD DATA
# ===============================
try:
    df = pd.read_csv('method_names_coded1.csv')
    print(f"\n✓ Loaded {len(df)} method names")
except FileNotFoundError:
    print("\n⚠ ERROR: 'method_names_coded1.csv' not found!")
    exit()

# ===============================
# QUALITY CLASSIFICATION
# ===============================

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

# Filter to humans only
df_participants = df[df['llm'].isin(['Human1', 'Human2', 'Original'])].copy()

human_high_quality = df_participants[df_participants['quality'] == 'High']
human_low_quality = df_participants[df_participants['quality'] == 'Low']
human_medium_quality = df_participants[df_participants['quality'] == 'Medium']

# ===============================
# TABLE 1: Quality Distribution per LLM
# ===============================
print("\n" + "="*70)
print("TABLE 1: Method names quality distribution per LLM")
print("="*70)

print(f"\n{'Category':30s} {'Item':25s} {'Count':>10s}")
print("-"*70)

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


# ===============================
# TABLE 1: Quality Distribution per Humans
# ===============================
print("\n" + "="*70)
print("TABLE 1 bis: Method names quality distribution per humans")
print("="*70)

print(f"\n{'Category':30s} {'Item':25s} {'Count':>10s}")
print("-"*70)

# Overall quality
print(f"{'Overall quality':30s} {'High-quality':25s} {len(human_high_quality):>10d}")
print(f"{'':30s} {'Low-quality':25s} {len(human_low_quality):>10d}")

print()

# High-quality per humans
print(f"{'High-quality per humans':30s} {'Human dev.1':25s} {len(human_high_quality[human_high_quality['llm']=='Human1']):>10d}")
print(f"{'':30s} {'Human dev.2':25s} {len(human_high_quality[human_high_quality['llm']=='Human2']):>10d}")
print(f"{'':30s} {'Original name':25s} {len(human_high_quality[human_high_quality['llm']=='Original']):>10d}")

print()

# Low-quality per humans
print(f"{'Low-quality per humans':30s} {'Human dev.1':25s} {len(human_low_quality[human_low_quality['llm']=='Human1']):>10d}")
print(f"{'':30s} {'Human dev.2':25s} {len(human_low_quality[human_low_quality['llm']=='Human2']):>10d}")
print(f"{'':30s} {'Original name':25s} {len(human_low_quality[human_low_quality['llm']=='Original']):>10d}")

print()

# High-quality per language
print(f"{'High-quality per language':30s} {'Java':25s} {len(human_high_quality[human_high_quality['language']=='Java']):>10d}")
print(f"{'':30s} {'Python':25s} {len(human_high_quality[human_high_quality['language']=='Python']):>10d}")
print(f"{'':30s} {'JavaScript':25s} {len(human_high_quality[human_high_quality['language']=='JavaScript']):>10d}")


# ===============================
# TABLE 2: Representative Examples
# ===============================
print("\n" + "="*70)
print("TABLE 2: Representative high- and low-quality method names from LLMs")
print("="*70)

print(f"\n{'Method name':35s} {'Lang':12s} {'LLM':8s} {'Quality':10s} {'Score':8s} {'Words':8s}")
print("-"*85)

print("HIGH-QUALITY EXAMPLES")
print("-"*85)

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

print("\nLOW-QUALITY EXAMPLES")
print("-"*85)

if len(low_quality) > 0:
    for idx, row in low_quality.iterrows():
        print(f"{row['actual_name']:35s} {row['language']:12s} {row['llm']:8s} {'Low':10s} {row['bad_count']:2d}/9{'':<4s} {row['word_count']:8d}")
else:
    print("No low-quality names found")


# ===============================
# TABLE 2 bis: Representative Examples
# ===============================
print("\n" + "="*70)
print("TABLE 2 bis: Representative high- and low-quality method names from humans")
print("="*70)

print(f"\n{'Method name':35s} {'Lang':12s} {'LLM':8s} {'Quality':10s} {'Score':8s} {'Words':8s}")
print("-"*85)

print("HIGH-QUALITY EXAMPLES")
print("-"*85)

# Get high-quality examples
human_high_examples = []
for llm in ['Human1', 'Human2', 'Original']:
    participants_high = human_high_quality[human_high_quality['llm'] == llm]
    if len(participants_high) > 0:
        best = participants_high.nlargest(2, 'good_count')
        for idx in range(min(2, len(best))):
            human_high_examples.append(best.iloc[idx])

for row in human_high_examples[:6]:
    print(f"{row['actual_name']:35s} {row['language']:12s} {row['llm']:8s} {'High':10s} {row['good_count']:2d}/9{'':<4s} {row['word_count']:8d}")

print("\nLOW-QUALITY EXAMPLES")
print("-"*85)

if len(human_low_quality) > 0:
    for idx, row in human_low_quality.iterrows():
        print(f"{row['actual_name']:35s} {row['language']:12s} {row['llm']:8s} {'Low':10s} {row['bad_count']:2d}/9{'':<4s} {row['word_count']:8d}")
else:
    print("No low-quality names found")


# =====================================
# TABLE 3: Structural Patterns for LLMs
# =====================================
print("\n" + "="*70)
print("TABLE 3: Structural patterns observed in high- and low-quality method names from LLMs")
print("="*70)

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


# =======================================
# TABLE 3: Structural Patterns for Humans
# =======================================
print("\n" + "="*70)
print("TABLE 3: Structural patterns observed in high- and low-quality method names from humans")
print("="*70)

# Calculate statistics
human_high_wc_mean = human_high_quality['word_count'].mean()
human_high_wc_median = human_high_quality['word_count'].median()
human_high_wc_min = human_high_quality['word_count'].min()
human_high_wc_max = human_high_quality['word_count'].max()

human_high_has_verb = (human_high_quality['has_verb'] == 'Yes').sum()
human_high_has_verb_pct = (high_has_verb / len(human_high_quality)) * 100

human_high_with_verbs = human_high_quality[human_high_quality['has_verb'] == 'Yes']
if len(human_high_with_verbs) > 0:
    human_high_specific = (human_high_with_verbs['verb_specificity'] == 'Specific').sum()
    human_high_specific_pct = (human_high_specific / len(human_high_with_verbs)) * 100
else:
    human_high_specific = 0
    human_high_specific_pct = 0

human_high_conv = (human_high_quality['follows_convention'] == 'Yes').sum()
human_high_conv_pct = (human_high_conv / len(human_high_quality)) * 100

# Low-quality statistics
if len(human_low_quality) > 0:
    human_low_wc_mean = human_low_quality['word_count'].mean()
    human_low_wc_median = human_low_quality['word_count'].median()
    human_low_wc_min = human_low_quality['word_count'].min()
    human_low_wc_max = human_low_quality['word_count'].max()
    
    human_low_has_verb = (human_low_quality['has_verb'] == 'Yes').sum()
    human_low_has_verb_pct = (human_low_has_verb / len(human_low_quality)) * 100
    
    human_low_with_verbs = human_low_quality[human_low_quality['has_verb'] == 'Yes']
    if len(human_low_with_verbs) > 0:
        human_low_specific = (human_low_with_verbs['verb_specificity'] == 'Specific').sum()
        human_low_specific_pct = (human_low_specific / len(human_low_with_verbs)) * 100
    else:
        human_low_specific = 0
        human_low_specific_pct = 0
    
    human_low_conv = (human_low_quality['follows_convention'] == 'Yes').sum()
    human_low_conv_pct = (human_low_conv / len(human_low_quality)) * 100
else:
    human_low_wc_mean = human_low_wc_median = human_low_wc_min = human_low_wc_max = 0
    human_low_has_verb = human_low_has_verb_pct = 0
    human_low_specific = human_low_specific_pct = 0
    human_low_conv = human_low_conv_pct = 0



print(f"\n{'Pattern':30s} {'High-quality for humans (n=' + str(len(human_high_quality)) + ')':30s} {'Low-quality for humans (n=' + str(len(human_low_quality)) + ')':30s}")
print("-"*95)

print(f"{'Mean word count':30s} {human_high_wc_mean:30.2f} {human_low_wc_mean:30.2f}")
print(f"{'Median word count':30s} {human_high_wc_median:30.1f} {human_low_wc_median:30.1f}")
print(f"{'Word count range':30s} {str(human_high_wc_min) + '-' + str(human_high_wc_max):30s} {str(human_low_wc_min) + '-' + str(human_low_wc_max):30s}")
print(f"{'Contains a verb':30s} {f'{human_high_has_verb}/{len(human_high_quality)} ({human_high_has_verb_pct:.1f}%)':30s} {f'{human_low_has_verb}/{len(human_low_quality)} ({human_low_has_verb_pct:.1f}%)':30s}")

if len(human_high_with_verbs) > 0 and len(human_low_with_verbs) > 0:
    print(f"{'Specific verb usage':30s} {f'{human_high_specific}/{len(human_high_with_verbs)} ({human_high_specific_pct:.1f}%)':30s} {f'{human_low_specific}/{len(human_low_with_verbs)} ({human_low_specific_pct:.1f}%)':30s}")
else:
    print(f"{'Specific verb usage':30s} {f'{human_high_specific}/{len(human_high_with_verbs)} ({human_high_specific_pct:.1f}%)' if len(human_high_with_verbs) > 0 else 'N/A':30s} {'N/A':30s}")

print(f"{'Convention adherence':30s} {f'{human_high_conv}/{len(human_high_quality)} ({human_high_conv_pct:.1f}%)':30s} {f'{human_low_conv}/{len(human_low_quality)} ({human_low_conv_pct:.1f}%)':30s}")

# ===============================
# TABLE 4: Patterns by Language and Source
# ===============================
print("\n" + "="*70)
print("TABLE 4: Structural patterns by programming language and source")
print("="*70)

def compute_metrics(data):
    """Compute all metrics for a given subset of data."""
    if len(data) == 0:
        return None
    wc_mean   = data['word_count'].mean()
    wc_median = data['word_count'].median()
    has_verb  = (data['has_verb'] == 'Yes').sum()
    has_verb_pct = has_verb / len(data) * 100
    with_verbs = data[data['has_verb'] == 'Yes']
    if len(with_verbs) > 0:
        specific     = (with_verbs['verb_specificity'] == 'Specific').sum()
        specific_pct = specific / len(with_verbs) * 100
    else:
        specific_pct = 0.0
    conv     = (data['follows_convention'] == 'Yes').sum()
    conv_pct = conv / len(data) * 100
    return {
        'n':            len(data),
        'wc_mean':      wc_mean,
        'wc_median':    wc_median,
        'verb_pct':     has_verb_pct,
        'specific_pct': specific_pct,
        'conv_pct':     conv_pct,
    }

def print_language_source_table(df_high, df_low, sources, section_label):
    header_source = ''.join([f"{s:>12s}" for s in sources])
    
    for quality_label, df_q in [('High-quality', df_high), ('Low-quality', df_low)]:
        print(f"\n--- {section_label} | {quality_label} (n={len(df_q)}) ---")
        print(f"\n{'':18s}{'Metric':22s}" + header_source)
        print("-" * (40 + 12 * len(sources)))

        metrics_list = ['n', 'wc_mean', 'wc_median', 'verb_pct', 'specific_pct', 'conv_pct']
        metric_labels = {
            'n':            'N',
            'wc_mean':      'Mean words',
            'wc_median':    'Median words',
            'verb_pct':     'Verb (%)',
            'specific_pct': 'Specific verb (%)',
            'conv_pct':     'Convention (%)',
        }

        for lang in ['Java', 'Python', 'JavaScript']:
            first_row = True
            for metric in metrics_list:
                label_col  = f"{lang:18s}" if first_row else f"{'':18s}"
                metric_col = f"{metric_labels[metric]:22s}"
                row_vals   = ""
                for source in sources:
                    subset = df_q[(df_q['language'] == lang) & (df_q['llm'] == source)]
                    m = compute_metrics(subset)
                    if m is None:
                        row_vals += f"{'N/A':>12s}"
                    elif metric == 'n':
                        row_vals += f"{int(m[metric]):>12d}"
                    elif metric in ('verb_pct', 'specific_pct', 'conv_pct'):
                        row_vals += f"{m[metric]:>11.1f}%"
                    else:
                        row_vals += f"{m[metric]:>12.2f}"
                print(label_col + metric_col + row_vals)
                first_row = False
            print("-" * (40 + 12 * len(sources)))

llm_sources   = ['Claude', 'GPT-5', 'Llama']
human_sources = ['Human1', 'Human2', 'Original']

# LLMs section
print_language_source_table(high_quality, low_quality, llm_sources, "LLMs")

# Humans section
print_language_source_table(human_high_quality, human_low_quality, human_sources, "Human participants")

print("\n" + "="*70)
print("END OF ANALYSIS")
print("="*70)
