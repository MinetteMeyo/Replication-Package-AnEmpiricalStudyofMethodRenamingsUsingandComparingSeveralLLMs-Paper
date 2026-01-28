import csv
import time
import requests
import tiktoken
import re

# ========== CONFIGURATION ==========
API_KEY = "0a62aec484719004430f8b114eab5bee96b89be9b33b975b3da5b8afbea6af49"
MODEL_NAME = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"

INPUT_CSV = "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/random_methods_python.csv"
OUTPUT_CSV = "/Users/durjoy/Documents/Lab CSSE/Result_files/Python/llama_suggestedMethodNames_python.csv"

MAX_TOKENS = 8192  # Stay safe for most models
RESPONSE_TOKENS = 300
PROMPT_TOKENS = 100

# ========== HELPER FUNCTIONS ==========

def count_tokens(text):
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))

def extract_method_body(file_path, method_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    pattern = r"def\s+" + re.escape(method_name) + r"\s*\("
    match = re.search(pattern, content)

    if not match:
        print(f"Method {method_name} not found in {file_path}")
        return None

    method_start = match.start()
    method_end = content.find('\n\n', method_start)
    if method_end == -1:
        method_end = len(content)

    method_body = content[method_start:method_end]
    return method_body

def extract_context(file_path, method_body):
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
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(context)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        context = encoder.decode(tokens)
    return context

def call_llama_with_retry(prompt, max_retries=10):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "AI assistant that generates method names based on method body and context."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": RESPONSE_TOKENS,
    }

    for i in range(max_retries):
        try:
            response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [422, 429]:
                wait_time = min(10 * (i + 1), 120)
                print(f"⚠️ {response.status_code} error, retry {i+1}, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise Exception(f"{response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ API request failed (retry {i+1}): {e}")
            time.sleep(10 * (i + 1))

    raise Exception("❌ Max retries exceeded for LLaMA API")

def generate_method_names(method_body, context):
    anonymized_body = re.sub(r"def\s+\w+", "def method_name", method_body, count=1)

    method_tokens = count_tokens(anonymized_body)
    available_context_tokens = MAX_TOKENS - (method_tokens + RESPONSE_TOKENS + PROMPT_TOKENS)

    context = truncate_context(context, available_context_tokens)

    prompt = f"""Method body (with method name anonymized):
{anonymized_body}

Context from surrounding code:
{context}

Provide method name suggestions as a numbered list, no explanations:"""

    try:
        result = call_llama_with_retry(prompt)
        return result["choices"][0]["message"]["content"].strip().split("\n")
    except Exception as e:
        print(f"❌ Error generating method names: {e}")
        return ["API_ERROR"]

# ========== MAIN PROCESS ==========

def process_csv(input_csv, output_csv, limit=20):
    try:
        with open(input_csv, 'r', encoding='utf-8') as infile, open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            header = next(reader, None)
            writer.writerow([
                "Fully Qualified Name",
                "File Path",
                "Method Name",
                "Method Body",
                "Context Tokens",
                "Context",
                "Suggested Names"
            ])

            count = 0
            for row in reader:
                if count >= limit:
                    print("✅ Finished processing 20 methods.")
                    break

                if len(row) < 3:
                    print(f"Skipping malformed row: {row}")
                    continue

                fully_qualified_name = row[0]
                file_path = row[1]
                method_name = fully_qualified_name.split("::")[-1] if "::" in fully_qualified_name else fully_qualified_name.split(".")[-1]

                print(f"\n🔍 Processing: {fully_qualified_name}")
                try:
                    method_body = extract_method_body(file_path, method_name)
                    if not method_body:
                        raise Exception("Method not found.")

                    context_before, context_after = extract_context(file_path, method_body)
                    context = context_before + context_after
                    context_tokens = count_tokens(context)

                    suggested_names = generate_method_names(method_body, context)

                    writer.writerow([
                        fully_qualified_name,
                        file_path,
                        method_name,
                        method_body,
                        context_tokens,
                        context,
                        ", ".join(suggested_names)
                    ])

                except Exception as e:
                    print(f"⚠️ Error processing {fully_qualified_name}: {e}")
                    writer.writerow([
                        fully_qualified_name,
                        file_path,
                        method_name,
                        "",
                        "",
                        "",
                        "ERROR"
                    ])

                count += 1
                time.sleep(3)  # avoid rate limits

        print(f"\n✅ Output saved to: {output_csv}")

    except Exception as e:
        print(f"❌ CSV processing failed: {e}")

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    process_csv(INPUT_CSV, OUTPUT_CSV, limit=20)
