// claude_method_name_suggester.js
// Node.js script to suggest method names using Claude 3.7 Sonnet API, ported from Python

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const Anthropic = require('@anthropic-ai/sdk');
require('dotenv').config();
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

// Load Anthropic API key from environment (.env or shell)
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const CLAUDE_MODEL = "claude-3-7-sonnet-20250219";

if (!ANTHROPIC_API_KEY) {
  console.error('ANTHROPIC_API_KEY is not set. Please add it to your .env file or environment.');
  process.exit(1);
}

// Initialize the Anthropic client with explicit API key
const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY });

// Max tokens for Claude 3.7 Sonnet is 200k but we use 16384
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

async function callClaudeWithRetry(messages, maxRetries = 5) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await anthropic.messages.create({
        model: CLAUDE_MODEL,
        system: "AI assistant that provides only method name suggestions in a numbered list format.",
        messages,
        temperature: 0.5,
        max_tokens: RESPONSE_TOKENS,
      });
      return response;
    } catch (e) {
      if (e.status === 429) {
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
    { role: 'user', content: prompt },
  ];
  try {
    const response = await callClaudeWithRetry(messages);
    const content = response.content[0].text.trim();
    return content.split('\n');
  } catch (e) {
    console.error(`Error calling Claude API: ${e}`);
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
  const outputCsv = '/Users/durjoy/Documents/Lab CSSE/NamingRefactoring/Result_files/JavaScript/claude_suggestedMethodNames_javaScript.csv';
  processCsv(inputCsv, outputCsv).catch(e => console.error(`Error processing CSV: ${e}`));
}
