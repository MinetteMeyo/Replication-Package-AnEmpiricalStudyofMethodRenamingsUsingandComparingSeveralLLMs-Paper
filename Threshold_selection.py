import re
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

# ============================================================================
# Configuration
# ============================================================================
CSV_FILE = "path_to_source_method_file"
OUTPUT_FILE = "outputFile.csv"
MIN_NAMES_REQUIRED = 20
CANDIDATE_THRESHOLDS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
    'self', 'none', 'true', 'false', 'not', 'has', 'have', 'def', 'if',
    'return',
}

def tokenize_identifier(identifier):
    """Split an identifier into lowercase tokens (camelCase / snake_case aware)."""
    identifier = identifier.replace('(', '').replace(')', '').replace('_', ' ')
    identifier = re.sub(r'([a-z])([A-Z])', r'\1 \2', identifier)
    return [t for t in identifier.lower().split() if t]


def extract_ground_truth_tokens(method_snippet):
    """Collect meaningful identifier tokens from the method body."""
    identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', method_snippet)
    tokens = set()
    for identifier in identifiers:
        if len(identifier) > 2:
            tokens.update(tokenize_identifier(identifier))
    return tokens - STOP_WORDS


def score_name(name, ground_truth_tokens):
    """Fraction of a candidate name's tokens that appear in the ground truth."""
    tokens = tokenize_identifier(name)
    if not tokens:
        return 0.0
    return sum(t in ground_truth_tokens for t in tokens) / len(tokens)


def parse_names(name_string):
    if pd.isna(name_string):
        return []
    name_string = str(name_string).replace('\n', ' ').replace('\r', ' ')
    return [n.strip() for n in name_string.split(',') if n.strip()]


def names_passing(scores, threshold):
    return sum(s >= threshold for s in scores)

def derive_threshold(all_scores, min_required):
    """
    Print a table of candidate thresholds vs. how many snippets keep at least
    `min_required` names, then pick the HIGHEST threshold for which every
    snippet still keeps >= min_required names. This is the justification for
    whichever threshold gets selected (e.g. 0.3 when min_required = 20).
    """
    print(f"Deriving threshold for MIN_NAMES_REQUIRED = {min_required}\n")
    print(f"{'threshold':>10s}{'snippets satisfied':>20s}"
          f"{'worse min. nber of names kept':>32s}")

    qualifying = []
    for t in CANDIDATE_THRESHOLDS:
        counts = [names_passing(scores, t) for scores in all_scores]
        snippets_ok = sum(c >= min_required for c in counts)
        print(f"{t:>10.1f}{snippets_ok:>13d}/{len(all_scores):<6d}"
              f"{min(counts):>19d}")
        if snippets_ok == len(all_scores):
            qualifying.append(t)

    best = max(qualifying) if qualifying else min(CANDIDATE_THRESHOLDS)
    print(f"\n-> Threshold {best} is the highest value for which ALL "
          f"{len(all_scores)} snippets keep >= {min_required} names.\n"
          f"   This is why {best} was selected.\n")
    return best

def jaccard_similarity(tokens_a, tokens_b):
    set_a, set_b = set(tokens_a), set(tokens_b)
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


def create_similarity_matrix(tokenized_names):
    n = len(tokenized_names)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            matrix[i][j] = 1.0 if i == j else jaccard_similarity(tokenized_names[i], tokenized_names[j])
    return matrix


def perform_clustering(similarity_matrix, n_clusters=2):
    distance_matrix = 1 - similarity_matrix
    linkage_matrix = linkage(squareform(distance_matrix), method='average')
    labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')

    clusters = {}
    for idx, cluster_id in enumerate(labels):
        clusters.setdefault(cluster_id, []).append(idx)
    return clusters


def select_cluster_exemplar(cluster_indices, similarity_matrix):
    """Return the index of the medoid (most representative member) of a cluster."""
    if len(cluster_indices) == 1:
        return cluster_indices[0]
    best_idx, best_avg_sim = cluster_indices[0], -1
    for idx in cluster_indices:
        sims = [similarity_matrix[idx][other] for other in cluster_indices if other != idx]
        avg_sim = np.mean(sims)
        if avg_sim > best_avg_sim:
            best_idx, best_avg_sim = idx, avg_sim
    return best_idx

def select_two_names_per_snippet(method_snippet, proposed_names, threshold):
    ground_truth_tokens = extract_ground_truth_tokens(method_snippet)

    scored = [(name, tokenize_identifier(name), score_name(name, ground_truth_tokens))
              for name in proposed_names]
    scored.sort(key=lambda x: x[2], reverse=True)

    filtered = [(name, tokens) for name, tokens, score in scored if score >= threshold]
    if not filtered:
        filtered = [(name, tokens) for name, tokens, score in scored[:min(10, len(scored))]]

    filtered_names = [name for name, _ in filtered]
    filtered_tokens = [tokens for _, tokens in filtered]

    if len(filtered_names) == 1:
        remaining = [name for name, _, _ in scored if name != filtered_names[0]]
        return (filtered_names[0], remaining[0]) if remaining else (filtered_names[0], filtered_names[0])

    similarity_matrix = create_similarity_matrix(filtered_tokens)
    clusters = perform_clustering(similarity_matrix, n_clusters=2)

    selected = []
    for cid in sorted(clusters.keys()):
        exemplar_idx = select_cluster_exemplar(clusters[cid], similarity_matrix)
        selected.append(filtered_names[exemplar_idx])

    if len(selected) < 2:
        selected.append(filtered_names[0])
    return selected[0], selected[1]
  
def main():
    df = pd.read_csv(CSV_FILE)
    df['suggested_names'] = df['suggested_names'].apply(parse_names)

    all_ground_truth = [extract_ground_truth_tokens(s) for s in df['method_snippet']]
    all_scores = [
        [score_name(name, gt) for name in names]
        for gt, names in zip(all_ground_truth, df['suggested_names'])
    ]

    print(f"{len(df)} method snippets loaded")
    print(f"Minimum names required per snippet: {MIN_NAMES_REQUIRED}\n")
    threshold = derive_threshold(all_scores, MIN_NAMES_REQUIRED)

    results = []
    for (idx, row), scores in zip(df.iterrows(), all_scores):
        snippet_id = row.get('snippet_id', idx + 1)
        names = row['suggested_names']
        if not names:
            continue
        name_1, name_2 = select_two_names_per_snippet(row['method_snippet'], names, threshold)
        results.append({'snippet_id': snippet_id, 'name_1': name_1, 'name_2': name_2})

    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

    results_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {len(results)} selections to {OUTPUT_FILE}")


main()
