import re
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import pandas as pd

# TOKENIZATION

def tokenize_identifier(identifier):
    """Split identifier into tokens handling camelCase and snake_case."""
    identifier = identifier.replace('(', '').replace(')', '')
    identifier = identifier.replace('_', ' ')
    identifier = re.sub(r'([a-z])([A-Z])', r'\1 \2', identifier)
    tokens = identifier.lower().split()
    return [t for t in tokens if t]

# GROUND TRUTH EXTRACTION

def extract_ground_truth_tokens(method_snippet):
    """Extract tokens from method snippet as ground truth."""
    tokens = set()
    identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', method_snippet)
    
    for identifier in identifiers:
        if len(identifier) > 2:
            tokens.update(tokenize_identifier(identifier))
    
    stop_words = {'the','a','an','and','or','but','in','on','at','to','for',
                  'of','with','by','from','as','is','was','are','be','been',
                  'self','none','true','false','not','has','have','def','if','return'}
    return tokens - stop_words

# SCORING

def calculate_ground_truth_score(proposed_tokens, ground_truth_tokens):
    if not proposed_tokens:
        return 0.0
    matching = sum(1 for token in proposed_tokens if token in ground_truth_tokens)
    return matching / len(proposed_tokens)

# JACCARD SIMILARITY

def jaccard_similarity(tokens_a, tokens_b):
    set_a, set_b = set(tokens_a), set(tokens_b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0

def create_similarity_matrix(tokenized_names):
    n = len(tokenized_names)
    similarity_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            similarity_matrix[i][j] = 1.0 if i == j else jaccard_similarity(tokenized_names[i], tokenized_names[j])
    return similarity_matrix

# CLUSTERING

def perform_clustering(similarity_matrix, n_clusters):
    distance_matrix = 1 - similarity_matrix
    condensed_distance = squareform(distance_matrix)
    linkage_matrix = linkage(condensed_distance, method='average')
    cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
    
    # Group by cluster
    clusters = {}
    for idx, cluster_id in enumerate(cluster_labels):
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(idx)
    
    return clusters

# EXEMPLAR SELECTION

def select_cluster_exemplar(cluster_indices, similarity_matrix):
    if len(cluster_indices) == 1:
        return cluster_indices[0]
    
    best_idx = None
    best_avg_sim = -1
    
    for idx in cluster_indices:
        similarities = [similarity_matrix[idx][other_idx] 
                       for other_idx in cluster_indices if idx != other_idx]
        avg_sim = np.mean(similarities)
        
        if avg_sim > best_avg_sim:
            best_avg_sim = avg_sim
            best_idx = idx
    
    return best_idx

def select_two_names_per_snippet(method_snippet, proposed_names, ground_truth_threshold=0.3, verbose=True):
    
    if verbose:
        print(f"  Step 1: Extracting ground truth tokens from method snippet...")
    
    # Extract ground truth
    ground_truth_tokens = extract_ground_truth_tokens(method_snippet)
    
    if verbose:
        print(f" Found {len(ground_truth_tokens)} ground truth tokens")
        print(f" Sample: {list(ground_truth_tokens)[:10]}")
    
    if verbose:
        print(f"\n  Step 2: Tokenizing and scoring {len(proposed_names)} proposed names...")
    
    # Tokenize and score all proposed names
    tokenized_names = [tokenize_identifier(name) for name in proposed_names]
    scores = [(name, tokens, calculate_ground_truth_score(tokens, ground_truth_tokens))
              for name, tokens in zip(proposed_names, tokenized_names)]
    
    # Sort by score for display
    scores_sorted = sorted(scores, key=lambda x: x[2], reverse=True)
    
    if verbose:
        print(f"    → Top 5 scoring names:")
        for name, tokens, score in scores_sorted[:5]:
            print(f"      • {name:40s} | score: {score:.2f} | tokens: {tokens}")
    
    # Filter by ground truth threshold
    filtered = [(name, tokens) for name, tokens, score in scores 
                if score >= ground_truth_threshold]
    
    if not filtered:
        if verbose:
            print(f"No names passed threshold {ground_truth_threshold}, using top 10")
        # If nothing passes, take top 10 by score
        filtered = [(name, tokens) for name, tokens, score in scores_sorted[:min(10, len(scores))]]
    
    if verbose:
        print(f"    → {len(filtered)} names passed filtering (threshold ≥ {ground_truth_threshold})")
    
    filtered_names = [name for name, tokens in filtered]
    filtered_tokens = [tokens for name, tokens in filtered]
    
    # If only 1 name after filtering, return it twice
    if len(filtered_names) == 1:
        if verbose:
            print(f"Only 1 name after filtering")
        # Try to find a second name from the unfiltered list
        if len(scores) > 1:
            remaining = [name for name, _, _ in scores if name not in filtered_names]
            if remaining:
                if verbose:
                    print(f"Adding next best name: {remaining[0]}")
                return (filtered_names[0], remaining[0])
        return (filtered_names[0], filtered_names[0])
    
    if verbose:
        print(f"\n  Step 3: Calculating Jaccard similarity matrix...")
    
    # Calculate similarity matrix
    similarity_matrix = create_similarity_matrix(filtered_tokens)
    
    if verbose:
        avg_sim = np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)])
        print(f"Average pairwise similarity: {avg_sim:.3f}")
    
    if verbose:
        print(f"\n  Step 4: Performing hierarchical clustering (k=2)...")
    
    # Perform clustering with k=2
    clusters = perform_clustering(similarity_matrix, n_clusters=2)
    
    if verbose:
        print(f"Created {len(clusters)} clusters:")
        for cluster_id, indices in sorted(clusters.items()):
            cluster_names = [filtered_names[i] for i in indices]
            print(f"Cluster {cluster_id} ({len(indices)} members): {cluster_names[:3]}{'...' if len(indices) > 3 else ''}")
    
    # If clustering creates only 1 cluster (shouldn't happen with k=2, but just in case)
    if len(clusters) == 1:
        if verbose:
            print(f"Only 1 cluster formed, manually selecting 2 most dissimilar names")
        # Pick the 2 most dissimilar names manually
        indices = clusters[list(clusters.keys())[0]]
        if len(indices) >= 2:
            # Find pair with minimum similarity
            min_sim = 2.0
            best_pair = (indices[0], indices[1])
            for i in range(len(indices)):
                for j in range(i+1, len(indices)):
                    sim = similarity_matrix[indices[i]][indices[j]]
                    if sim < min_sim:
                        min_sim = sim
                        best_pair = (indices[i], indices[j])
            if verbose:
                print(f"    → Selected pair with similarity: {min_sim:.3f}")
            return (filtered_names[best_pair[0]], filtered_names[best_pair[1]])
        else:
            return (filtered_names[indices[0]], filtered_names[indices[0]])
    
    if verbose:
        print(f"\n  Step 5: Selecting exemplar (medoid) from each cluster...")
    
    # Select exemplar from each cluster
    selected_names = []
    for cluster_id in sorted(clusters.keys()):
        exemplar_idx = select_cluster_exemplar(clusters[cluster_id], similarity_matrix)
        exemplar_name = filtered_names[exemplar_idx]
        
        if verbose:
            # Calculate representativeness
            cluster_indices = clusters[cluster_id]
            if len(cluster_indices) > 1:
                similarities = [similarity_matrix[exemplar_idx][other_idx] 
                               for other_idx in cluster_indices if exemplar_idx != other_idx]
                avg_sim = np.mean(similarities)
            else:
                avg_sim = 1.0
            print(f"Cluster {cluster_id} exemplar: {exemplar_name} (representativeness: {avg_sim:.3f})")
        
        selected_names.append(exemplar_name)
    
    # Return exactly 2 names
    if len(selected_names) >= 2:
        return (selected_names[0], selected_names[1])
    else:
        # This shouldn't happen, but fallback
        return (selected_names[0], filtered_names[0] if filtered_names else selected_names[0])
      
# BATCH PROCESSING

CSV_FILE = "../method_names.csv"
OUTPUT_FILE = "selected_names_per_snippet.csv"
GROUND_TRUTH_THRESHOLD = 0.3

print(f"Reading CSV from: {CSV_FILE}")
df = pd.read_csv(CSV_FILE)
print(f"Total snippets: {len(df)}\n")

# Parse suggested names and clean them
def parse_and_clean_names(name_string):
    if pd.isna(name_string):
        return []
    # Replace newlines and extra whitespace
    name_string = str(name_string).replace('\n', ' ').replace('\r', ' ')
    # Split by comma
    names = [name.strip() for name in name_string.split(',')]
    # Remove empty strings and clean each name
    names = [n for n in names if n]
    return names

df['suggested_names'] = df['suggested_names'].apply(parse_and_clean_names)

# Process each snippet
results = []

for idx, row in df.iterrows():
    snippet_id = row.get('snippet_id', idx + 1)
    snippet = row['method_snippet']
    names = row['suggested_names']
    
    if not names:
        print(f"\n{'='*70}")
        print(f"SNIPPET {snippet_id}: SKIPPED (no suggested names)")
        print(f"{'='*70}")
        continue
    
    print(f"\n{'='*70}")
    print(f"SNIPPET {snippet_id}: Processing {len(names)} suggested names")
    print(f"{'='*70}")
    
    name_1, name_2 = select_two_names_per_snippet(snippet, names, GROUND_TRUTH_THRESHOLD, verbose=True)
    
    # Debug: show if names are identical
    if name_1 == name_2:
        print(f"\n Both names are identical")
    
    results.append({
        'snippet_id': snippet_id,
        'name_1': name_1,
        'name_2': name_2
    })
    
    print(f"\n FINAL SELECTION:")
    print(f"    Name 1: {name_1}")
    print(f"    Name 2: {name_2}")

# Save results
output_df = pd.DataFrame(results)
output_df.to_csv(OUTPUT_FILE, index=False)

