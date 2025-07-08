import os
import csv
import random
import ast

def extract_method_body(filepath, node):
    """Extracts the full method body with accurate scope handling."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.readlines()
        
        # Get the line range for the method
        start_line = node.lineno - 1  # 0-indexed
        end_line = node.end_lineno
        
        # Extract the method source code
        method_source = ''.join(code[start_line:end_line])
        return method_source
    except Exception as e:
        print(f"Error extracting method body: {e}")
        return "N/A"

def count_non_comment_lines(method_text):
    """Count non-comment, non-blank lines in a method."""
    lines = method_text.split('\n')
    count = 0
    in_block_comment = False  # For handling multi-line docstrings
    
    for line in lines:
        # Remove leading/trailing whitespace
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
            
        # Handle multi-line docstrings and comments
        if in_block_comment:
            if stripped.endswith('"""') or stripped.endswith("'''"):
                in_block_comment = False
            continue
            
        # Check for docstring or comment start
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if (stripped.endswith('"""') and not stripped.startswith('"""""""')) or \
               (stripped.endswith("'''") and not stripped.startswith("''''''")): 
                # Single line docstring
                continue
            else:
                # Start of multi-line docstring
                in_block_comment = True
                continue
                
        # Check for line comments
        if stripped.startswith("#"):
            continue
            
        # If we've reached here, it's a code line
        count += 1
    
    return count

def is_test_method(method_name, file_path):
    """Check if a method is likely a test method."""
    if 'test' in method_name.lower():
        return True
    if 'test' in file_path.lower():
        return True
    return False

def find_methods(filepath, target_lines, variance):
    """Finds all methods in a Python file that match criteria."""
    methods = []
    
    # Skip large files
    if os.path.getsize(filepath) > 1000000:  # 1MB
        print(f"⚠️ Skipping large file: {filepath}")
        return methods
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
            
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                method_name = node.name
                
                # Skip test methods and magic methods
                if is_test_method(method_name, filepath) or (method_name.startswith('__') and method_name.endswith('__')):
                    continue
                
                # Skip simple methods (just a pass or a single return)
                if len(node.body) <= 1:
                    if isinstance(node.body[0], ast.Pass) or isinstance(node.body[0], ast.Return):
                        continue
                
                # Extract method body
                method_body = extract_method_body(filepath, node)
                
                # Count actual code lines
                line_count = count_non_comment_lines(method_body)
                
                # Check if the method is within the target line count range
                if target_lines - variance <= line_count <= target_lines + variance:
                    # Determine fully qualified name based on context
                    # Get module name from filepath
                    module_name = os.path.basename(filepath).replace('.py', '')
                    fully_qualified_name = f"{module_name}::{method_name}"
                    
                    methods.append([fully_qualified_name, filepath, method_name, method_body, line_count])
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    
    return methods

def process_repositories(directories, output_csv, target_lines=50, variance=20):
    """Processes repositories and selects methods of target line count."""
    data = [["Fully Qualified Name", "File Path", "Method Name", "Method Body", "Line Count"]]
    files_processed = 0
    skipped_files = 0
    all_methods = []

    for directory in directories:
        if not os.path.exists(directory):
            print(f"⚠️ Directory not found: {directory}")
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root, file)
                    try:
                        file_methods = find_methods(file_path, target_lines, variance)
                        
                        if file_methods:
                            all_methods.extend(file_methods)
                            files_processed += 1
                            print(f"  Found {len(file_methods)} methods in {file_path}")
                        else:
                            skipped_files += 1
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        skipped_files += 1

    # Select up to 20 random methods, or all if fewer than 20
    selected_methods = all_methods
    if len(all_methods) > 20:
        selected_methods = random.sample(all_methods, 20)
    
    # If we don't have enough methods, expand the variance and try again
    if len(selected_methods) < 20 and variance < 40:  # Limit recursion
        print(f"⚠️ Only found {len(selected_methods)} methods. Trying with expanded variance...")
        # Recursively call with greater variance
        return process_repositories(directories, output_csv, target_lines, variance + 10)

    # Write results to CSV
    if selected_methods:
        data.extend(selected_methods)
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)
        print(f"✅ CSV generated: {output_csv}")
        print(f"✅ Processed {files_processed} files, skipped {skipped_files} files")
        print(f"✅ Found {len(all_methods)} methods in target range, wrote {len(selected_methods)} to CSV.")
    else:
        print(f"⚠️ No methods found with {target_lines}±{variance} lines. Try adjusting the target or variance.")
    
    return len(selected_methods)

if __name__ == "__main__":
    repositories = [
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/python/system-design-primer",
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/python/stable-diffusion-webui",
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/python/transformers"
    ]
    process_repositories(repositories, "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/random_methods_python.csv", target_lines=50, variance=20)