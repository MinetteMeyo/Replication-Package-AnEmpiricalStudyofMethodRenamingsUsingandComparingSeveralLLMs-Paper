import csv
import tiktoken
import re
import os
import anthropic
from anthropic import Anthropic

ANTHROPIC_API_KEY = "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"


# Initialize the Anthropic client with explicit API key
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Max tokens for Claude 3.7 Sonnet is 200k but we use 4096
MAX_TOKENS = 16384

# Token allocation - adjust these values based on your priorities
RESPONSE_TOKENS = 300  # Increased from 100 to get more complete responses
PROMPT_OVERHEAD = 50   # Fixed overhead for prompt instructions

def count_tokens(text):
    """Count the number of tokens in a given text using tiktoken."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def extract_method_body(file_path, method_name):
    """Extract method body from the file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    # Find the method definition
    pattern = r"def\s+" + re.escape(method_name) + r"\s*\("
    match = re.search(pattern, content)
    
    if not match:
        print(f"Method {method_name} not found in {file_path}")
        return None

    # Extract the method body
    method_start = match.start()
    method_end = content.find('\n\n', method_start)  # Assuming method ends with an empty line

    if method_end == -1:
        method_end = len(content)

    method_body = content[method_start:method_end]
    return method_body

def extract_context(file_path, method_body):
    """Extract context before and after the method."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, None

    method_start = content.find(method_body)
    method_end = method_start + len(method_body)

    context_before = content[:method_start]
    context_after = content[method_end:]

    return context_before, context_after

def generate_method_names(method_body, context):
    """Generate method names using Claude API."""
    prompt = f"""Method body (with method name anonymized):
{method_body}

Context from surrounding code:
{context}

Provide method name suggestions as a numbered list, no explanations:"""

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            system="AI assistant that provides only method name suggestions in a numbered list format.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=RESPONSE_TOKENS,
        )
        return response.content[0].text.strip().split("\n")
    except Exception as e:
        print(f"API error: {e}")
        return ["N/A"]

def process_csv(input_csv, output_csv):
    """Process the input CSV file and generate method names."""
    try:
        with open(input_csv, 'r', encoding='utf-8') as infile, open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # Read header
            header = next(reader, None)
            
            # Write header
            writer.writerow([
                "Fully Qualified Name", 
                "File Path", 
                "Method Name", 
                "Method Body", 
                "Context Tokens", 
                "Context", 
                "Suggested Names"
            ])
            
            for row in reader:
                if len(row) < 3:
                    print(f"Warning: Row has fewer than 3 columns: {row}")
                    continue
                
                fully_qualified_name = row[0]
                file_path = row[1]
                method_description = row[2]  # This column is not used in this script
                
                # Extract method name from fully qualified name
                if '::' in fully_qualified_name:
                    method_name = fully_qualified_name.split('::')[-1]
                else:
                    method_name = fully_qualified_name.split('.')[-1]
                
                print(f"Processing: {fully_qualified_name}")
                
                # Extract method body
                method_body = extract_method_body(file_path, method_name)
                
                if not method_body:
                    print(f"Method {method_name} not found in {file_path}")
                    writer.writerow([
                        fully_qualified_name, 
                        file_path, 
                        method_name, 
                        "", 
                        "", 
                        "", 
                        "METHOD_NOT_FOUND"
                    ])
                    continue
                
                # Extract context
                context_before, context_after = extract_context(file_path, method_body)
                context = context_before + context_after
                
                # Count tokens in context
                context_tokens = count_tokens(context)
                
                # Anonymize method name
                anonymized_body = re.sub(r"def\s+\w+", "def method_name", method_body, 1)
                
                # Generate method names
                suggested_names = generate_method_names(anonymized_body, context)
                
                # Write to CSV
                writer.writerow([
                    fully_qualified_name,
                    file_path,
                    method_name,
                    method_body,  # Write the actual method body
                    context_tokens,  # Write the number of tokens in the context
                    context,  # Write the context itself
                    ", ".join(suggested_names)
                ])
        
        print(f"✅ Output saved to {output_csv}")
    
    except Exception as e:
        print(f"Error processing CSV: {e}")

if __name__ == "__main__":
    # Hardcode the input and output file paths here
    input_csv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/random_methods_python.csv"  # Replace with your input CSV file path
    output_csv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/claude_suggestedMethodNames_python.csv"  # Replace with your output CSV file path
    
    # Process the CSV
    process_csv(input_csv, output_csv)