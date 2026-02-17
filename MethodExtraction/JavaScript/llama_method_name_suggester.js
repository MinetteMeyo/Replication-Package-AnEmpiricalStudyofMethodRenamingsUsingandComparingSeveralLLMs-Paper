// llama_method_name_suggester.js
// Node.js script to suggest method names using Llama API, ported from Python

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const axios = require('axios');
let encoding;

// Try to use tiktoken-node, fallback to gpt-3-encoder
try {
  encoding = require('tiktoken-node').encoding_for_model('cl100k_base');
} catch (e) {
  try {
    encoding = require('gpt-3-encoder');
  } catch (e2) {
    console.error('Please install tiktoken-node or gpt-3-encoder for token counting.');
    process.exit(1);
  }
}

// Set your Llama API key
const LLAMA_API_KEY = "0a62aec484719004430f8b114eab5bee96b89be9b33b975b3da5b8afbea6af49";
const LLAMA_MODEL = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8";
const LLAMA_API_URL = "https://api.together.xyz/v1/chat/completions";

if (!LLAMA_API_KEY) {
  console.error('Please set your LLAMA_API_KEY environment variable.');
  process.exit(1);
}

const MAX_TOKENS = 16384;
const RESPONSE_TOKENS = 300;
const PROMPT_TOKENS = 100;

function countTokens(text) {
  if (encoding.encode) {
    return encoding.encode(text).length;
  } else {
    // tiktoken-node
    return encoding.encode(text).length;
  }
}

function anonymizeMethodName(methodBody, methodName) {
  // Anonymize JavaScript function declaration: function foo(...) -> function method_name(...)
  // Aligns with Java/Python: Java anonymizes signature, Python anonymizes def foo
  const escaped = methodName.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
  return methodBody.replace(new RegExp(`function\\s+${escaped}\\s*\\(`), 'function method_name(');
}

function extractContext(filePath, methodBody) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const methodStart = content.indexOf(methodBody);
    const methodEnd = methodStart + methodBody.length;
    const contextBefore = content.substring(0, methodStart);
    const contextAfter = content.substring(methodEnd);
    return { contextBefore, contextAfter };
  } catch (e) {
    console.error(`Error reading ${filePath}: ${e}`);
    return { contextBefore: '', contextAfter: '' };
  }
}

function truncateContext(context, maxTokens) {
  const tokens = encoding.encode(context);
  if (tokens.length > maxTokens) {
    return encoding.decode(tokens.slice(0, maxTokens));
  }
  return context;
}

async function callLlamaWithRetry(messages, maxRetries = 5) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await axios.post(LLAMA_API_URL, {
        model: LLAMA_MODEL,
        messages,
        temperature: 0.5,
        max_tokens: RESPONSE_TOKENS,
      }, {
        headers: {
          'Authorization': `Bearer ${LLAMA_API_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      return response.data;
    } catch (e) {
      if (e.response && e.response.status === 429) {
        const waitTime = 20 * (i + 1);
        console.log(`Rate limit hit, retrying after ${waitTime} seconds...`);
        await new Promise(res => setTimeout(res, waitTime * 1000));
      } else {
        throw e;
      }
    }
  }
  throw new Error('Exceeded max retries due to rate limits.');
}

async function generateMethodNames(methodBody, context, methodName) {
  // Anonymize the method name (JavaScript: function foo(...) -> function method_name(...))
  const anonymizedBody = anonymizeMethodName(methodBody, methodName);
  const methodTokens = countTokens(anonymizedBody);
  const availableTokens = MAX_TOKENS - (methodTokens + RESPONSE_TOKENS + PROMPT_TOKENS);
  const truncatedContext = truncateContext(context, availableTokens);
  const prompt = `Method body (with method name anonymized):\n${anonymizedBody}\n\nContext from surrounding code:\n${truncatedContext}\n\nProvide method name suggestions as a numbered list, no explanations:`;
  const messages = [
    { role: 'system', content: 'AI assistant that generates method names based on method body and context.' },
    { role: 'user', content: prompt },
  ];
  try {
    const response = await callLlamaWithRetry(messages);
    const content = response.choices[0].message.content.trim();
    return content.split('\n');
  } catch (e) {
    console.error(`Error calling Llama API: ${e}`);
    return ['N/A'];
  }
}

async function processCsv(inputCsv, outputCsv) {
  const rows = [];
  // Read CSV
  await new Promise((resolve, reject) => {
    fs.createReadStream(inputCsv)
      .pipe(csv())
      .on('data', (row) => rows.push(row))
      .on('end', resolve)
      .on('error', reject);
  });

  // Prepare CSV writer
  const csvWriter = createCsvWriter({
    path: outputCsv,
    header: [
      { id: 'fullyQualifiedName', title: 'Fully Qualified Name' },
      { id: 'filePath', title: 'File Path' },
      { id: 'methodName', title: 'Method Name' },
      { id: 'methodBody', title: 'Method Body' },
      { id: 'contextTokens', title: 'Context Tokens' },
      { id: 'context', title: 'Context' },
      { id: 'suggestedNames', title: 'Suggested Names' },
    ],
  });

  const outputRows = [];
  for (const row of rows) {
    const fullyQualifiedName = row['Fully Qualified Name'] ?? row[Object.keys(row)[0]];
    const filePath = row['File Path'] ?? row[Object.keys(row)[1]];
    const methodName = row['Method Name'] ?? (fullyQualifiedName.includes('::') ? fullyQualifiedName.split('::').pop() : fullyQualifiedName.split('.').pop());
    const methodBody = row['Method Body'] ?? row[Object.keys(row)[3]];
    console.log(`Processing: ${fullyQualifiedName}`);
    if (!methodBody || !methodBody.trim()) {
      console.log(`Method ${methodName} has no body in CSV (skipping)`);
      outputRows.push({
        fullyQualifiedName,
        filePath,
        methodName,
        methodBody: '',
        contextTokens: '',
        context: '',
        suggestedNames: 'METHOD_NOT_FOUND',
      });
      continue;
    }
    const { contextBefore, contextAfter } = extractContext(filePath, methodBody);
    const context = contextBefore + contextAfter;
    const contextTokens = countTokens(context);
    const suggestedNames = await generateMethodNames(methodBody, context, methodName);
    outputRows.push({
      fullyQualifiedName,
      filePath,
      methodName,
      methodBody,
      contextTokens,
      context,
      suggestedNames: suggestedNames.join(', '),
    });
  }
  await csvWriter.writeRecords(outputRows);
  console.log(`✅ Output saved to ${outputCsv}`);
}

// MAIN
if (require.main === module) {
  // Hardcode or get from args
  const inputCsv = '/Users/durjoy/Documents/Lab CSSE/NamingRefactoring/Result_files/JavaScript/random_methods_javascript.csv';
  const outputCsv = '/Users/durjoy/Documents/Lab CSSE/NamingRefactoring/Result_files/JavaScript/llama_suggestedMethodNames_javaScript.csv';
  processCsv(inputCsv, outputCsv).catch(e => console.error(`Error processing CSV: ${e}`));
}
