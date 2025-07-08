// method_name_suggester.js
// Node.js script to suggest method names using OpenAI API, ported from Python

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const OpenAI = require('openai');
let encoding;

// Try to use tiktoken-node, fallback to gpt-3-encoder
try {
  encoding = require('tiktoken-node').encoding_for_model('gpt-4');
} catch (e) {
  try {
    encoding = require('gpt-3-encoder');
  } catch (e2) {
    console.error('Please install tiktoken-node or gpt-3-encoder for token counting.');
    process.exit(1);
  }
}

// Set your OpenAI API key via environment variable

// Manually set your OpenAI API key (as in the Python example)
const OPENAI_API_KEY = "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";
if (!OPENAI_API_KEY) {
  console.error('Please set your OpenAI_API_KEY environment variable.');
  process.exit(1);
}

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

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

function extractMethodBody(filePath, methodName) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    let match = null;
    let pattern;

    // 1. function declarations: function methodName(...) { ... }
    pattern = new RegExp(`function\\s+${methodName.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\s*\\([^)]*\\)\\s*{`, 'g');
    match = pattern.exec(content);

    // 2. class/object methods: methodName(...) { ... }
    if (!match) {
      pattern = new RegExp(`(^|[\s;])${methodName.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\s*\\([^)]*\\)\\s*{`, 'g');
      match = pattern.exec(content);
    }

    // 3. arrow functions: const methodName = (...) => { ... }
    if (!match) {
      pattern = new RegExp(`(const|let|var)\\s+${methodName.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\s*=\\s*\\([^)]*\\)\\s*=>\\s*{`, 'g');
      match = pattern.exec(content);
    }

    if (!match) return null;

    const methodStart = match.index;
    // Find the matching closing brace for the function body
    let openBraces = 0, i = match.index;
    let started = false;
    for (; i < content.length; i++) {
      if (content[i] === '{') {
        openBraces++;
        started = true;
      } else if (content[i] === '}') {
        openBraces--;
      }
      if (started && openBraces === 0) break;
    }
    const methodBody = content.substring(methodStart, i + 1);
    return methodBody;
  } catch (e) {
    console.error(`Error reading ${filePath}: ${e}`);
    return null;
  }
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

async function callOpenAIWithRetry(messages, maxRetries = 5) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4o',
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

async function generateMethodNames(methodBody, context) {
  // Anonymize the method name
  const anonymizedBody = methodBody.replace(/def\s+\w+/, 'def method_name');
  const methodTokens = countTokens(anonymizedBody);
  const availableTokens = MAX_TOKENS - (methodTokens + RESPONSE_TOKENS + PROMPT_TOKENS);
  const truncatedContext = truncateContext(context, availableTokens);
  const prompt = `Method body (with method name anonymized):\n${anonymizedBody}\n\nContext from surrounding code:\n${truncatedContext}\n\nProvide method name suggestions as a numbered list, no explanations:`;
  const messages = [
    { role: 'system', content: 'AI assistant that generates method names based on method body and context.' },
    { role: 'user', content: prompt },
  ];
  try {
    const response = await callOpenAIWithRetry(messages);
    const content = response.choices[0].message.content.trim();
    return content.split('\n');
  } catch (e) {
    console.error(`Error calling OpenAI API: ${e}`);
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
    const fullyQualifiedName = row[Object.keys(row)[0]];
    const filePath = row[Object.keys(row)[1]];
    const methodDescription = row[Object.keys(row)[2]];
    let methodName;
    if (fullyQualifiedName.includes('::')) {
      methodName = fullyQualifiedName.split('::').pop();
    } else {
      methodName = fullyQualifiedName.split('.').pop();
    }
    console.log(`Processing: ${fullyQualifiedName}`);
    const methodBody = extractMethodBody(filePath, methodName);
    if (!methodBody) {
      console.log(`Method ${methodName} not found in ${filePath}`);
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
    const suggestedNames = await generateMethodNames(methodBody, context);
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
  const inputCsv = '/Users/durjoy/Documents/Lab CSSE/Result_files/JavaScript/random_methods_javascript.csv';
  const outputCsv = '/Users/durjoy/Documents/Lab CSSE/Result_files/JavaScript/gpt4o_suggestedMethodNames_javaScript.csv';
  processCsv(inputCsv, outputCsv).catch(e => console.error(`Error processing CSV: ${e}`));
} 