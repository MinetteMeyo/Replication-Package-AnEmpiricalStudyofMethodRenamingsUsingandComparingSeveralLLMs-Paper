import csv
import time
import openai
import tiktoken
import re
from openai.error import RateLimitError  # Ensure this is imported

# Manually set your OpenAI API key
openai.api_key = "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"

# Define the retry wrapper here
def call_openai_with_retry(messages, max_retries=5):
    for i in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.5,
                max_tokens=300,
            )
            return response
        except RateLimitError as e:
            wait_time = 20 * (i + 1)
            print(f"Rate limit hit, retrying after {wait_time} seconds...")
            time.sleep(wait_time)
    raise Exception("Exceeded max retries due to rate limits.")

MAX_TOKENS = 16384  # Token limit for GPT-4
RESPONSE_TOKENS = 300  # Tokens reserved for the response
PROMPT_TOKENS = 100  # Tokens reserved for the prompt instructions

def count_tokens(text):
    """Counts the number of tokens in a given text."""
    encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    return len(encoder.encode(text))

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

def truncate_context(context, max_tokens):
    """Truncate the context to fit within the token limit."""
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(context)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        context = encoder.decode(tokens)
    return context

def generate_method_names(method_body, context):
    """Generate method names using GPT-4o."""
    # Anonymize the method name
    anonymized_body = re.sub(r"def\s+\w+", "def method_name", method_body, 1)

    # Calculate available tokens for the context
    method_tokens = count_tokens(anonymized_body)
    available_tokens = MAX_TOKENS - (method_tokens + RESPONSE_TOKENS + PROMPT_TOKENS)

    # Truncate the context if necessary
    context = truncate_context(context, available_tokens)

    # Construct the prompt
    prompt = f"""Method body (with method name anonymized):
{anonymized_body}

Context from surrounding code:
{context}

Provide method name suggestions as a numbered list, no explanations:"""

    try:
        messages=[
            {"role": "system", "content": "AI assistant that generates method names based on method body and context."},
            {"role": "user", "content": prompt},
        ]

        response = call_openai_with_retry(messages)
        # response = openai.ChatCompletion.create(
        #     model="gpt-4o",  # Use GPT-4o
        #     messages=[
        #         {"role": "system", "content": "AI assistant that generates method names based on method body and context."},
        #         {"role": "user", "content": prompt},
        #     ],
        #     temperature=0.5,
        #     max_tokens=RESPONSE_TOKENS,
        # )
        return response.choices[0].message['content'].strip().split("\n")
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
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
                
                # Generate method names
                suggested_names = generate_method_names(method_body, context)
                
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
    output_csv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/gpt4o_suggestedMethodNames_python.csv"  # Replace with your output CSV file path
    
    # Process the CSV
    process_csv(input_csv, output_csv)