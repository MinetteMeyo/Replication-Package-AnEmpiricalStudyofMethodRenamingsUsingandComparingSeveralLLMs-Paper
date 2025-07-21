const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const csv = require('csv-writer').createObjectCsvWriter;

function extractMethodBody(filepath, node, sourceCode) {
    // Extracts the full method body with accurate scope handling.
    try {
        // Get the start and end positions for the method
        const startPos = node.start;
        const endPos = node.end;
        
        // Extract the method source code
        const methodSource = sourceCode.substring(startPos, endPos);
        return methodSource;
    } catch (error) {
        console.log(`Error extracting method body: ${error}`);
        return "N/A";
    }
}

function countNonCommentLines(methodText) {
    // Count non-comment, non-blank lines in a method.
    const lines = methodText.split('\n');
    let count = 0;
    let inBlockComment = false;
    let inLineComment = false;
    
    for (let line of lines) {
        // Remove leading/trailing whitespace
        const stripped = line.trim();
        
        // Skip empty lines
        if (!stripped) {
            continue;
        }
        
        // Handle multi-line comments
        if (inBlockComment) {
            if (stripped.includes('*/')) {
                inBlockComment = false;
                // Check if there's code after the comment ends
                const afterComment = stripped.split('*/')[1];
                if (afterComment && afterComment.trim()) {
                    count++;
                }
            }
            continue;
        }
        
        // Check for start of block comment
        if (stripped.includes('/*')) {
            inBlockComment = true;
            // Check if there's code before the comment starts
            const beforeComment = stripped.split('/*')[0];
            if (beforeComment && beforeComment.trim()) {
                count++;
            }
            // Check if comment ends on same line
            if (stripped.includes('*/')) {
                inBlockComment = false;
                const afterComment = stripped.split('*/')[1];
                if (afterComment && afterComment.trim()) {
                    count++;
                }
            }
            continue;
        }
        
        // Check for line comments
        if (stripped.startsWith('//')) {
            continue;
        }
        
        // Check for JSDoc comments
        if (stripped.startsWith('/**') || stripped.startsWith('*')) {
            continue;
        }
        
        // If we've reached here, it's a code line
        count++;
    }
    
    return count;
}

function isTestMethod(methodName, filePath) {
    // Check if a method is likely a test method.
    if (methodName.toLowerCase().includes('test')) {
        return true;
    }
    if (filePath.toLowerCase().includes('test')) {
        return true;
    }
    return false;
}

function findMethods(filepath, targetLines, variance) {
    // Finds all top-level named function declarations in a JavaScript file that match criteria.
    const methods = [];
    
    // Skip large files
    const stats = fs.statSync(filepath);
    if (stats.size > 1000000) { // 1MB
        console.log(`⚠️ Skipping large file: ${filepath}`);
        return methods;
    }
    
    try {
        const code = fs.readFileSync(filepath, 'utf8');
        
        // Parse with Acorn
        const ast = acorn.parse(code, {
            ecmaVersion: 2020,
            sourceType: 'module',
            locations: true
        });
        
        // Only walk top-level nodes
        if (ast.body && Array.isArray(ast.body)) {
            for (const node of ast.body) {
                if (node.type === 'FunctionDeclaration' && node.id && typeof node.id.name === 'string' && node.id.name.trim() !== '') {
                    const methodName = node.id.name;
                    // Skip test methods and magic methods and constructors
                    if (isTestMethod(methodName, filepath) ||
                        (methodName.startsWith('_') && methodName.endsWith('_')) ||
                        methodName === 'constructor') {
                        continue;
                    }
                    // Skip simple methods (just a return or single expression)
                    if (node.body && node.body.type === 'BlockStatement') {
                        if (node.body.body.length <= 1) {
                            const firstStmt = node.body.body[0];
                            if (!firstStmt || 
                                firstStmt.type === 'ReturnStatement' ||
                                firstStmt.type === 'ExpressionStatement') {
                                continue;
                            }
                        }
                    }
                    // Extract method body
                    const methodBody = extractMethodBody(filepath, node, code);
                    // Count actual code lines
                    const lineCount = countNonCommentLines(methodBody);
                    // Check if the method is within the target line count range
                    if (targetLines - variance <= lineCount && lineCount <= targetLines + variance) {
                        // Determine fully qualified name based on context
                        const moduleName = path.basename(filepath, '.js');
                        const fullyQualifiedName = `${moduleName}::${methodName}`;
                        methods.push([fullyQualifiedName, filepath, methodName, methodBody, lineCount]);
                    }
                }
            }
        }
    } catch (error) {
        console.log(`Error processing ${filepath}: ${error}`);
    }
    
    return methods;
}

function processRepositories(directories, outputCsv, targetLines = 50, variance = 20) {
    // Processes repositories and selects methods of target line count.
    const data = [["Fully Qualified Name", "File Path", "Method Name", "Method Body", "Line Count"]];
    let filesProcessed = 0;
    let skippedFiles = 0;
    let allMethods = [];

    for (const directory of directories) {
        if (!fs.existsSync(directory)) {
            console.log(`⚠️ Directory not found: ${directory}`);
            continue;
        }
        
        function walkDir(dir) {
            const files = fs.readdirSync(dir);
            
            for (const file of files) {
                const filePath = path.join(dir, file);
                const stat = fs.statSync(filePath);
                
                if (stat.isDirectory()) {
                    walkDir(filePath);
                } else if (file.endsWith('.js') && !file.startsWith('__')) {
                    try {
                        const fileMethods = findMethods(filePath, targetLines, variance);
                        
                        if (fileMethods.length > 0) {
                            allMethods.push(...fileMethods);
                            filesProcessed++;
                            console.log(`  Found ${fileMethods.length} methods in ${filePath}`);
                        } else {
                            skippedFiles++;
                        }
                    } catch (error) {
                        console.log(`Error processing ${filePath}: ${error}`);
                        skippedFiles++;
                    }
                }
            }
        }
        
        walkDir(directory);
    }

    // Select up to 20 random methods, or all if fewer than 20
    let selectedMethods = allMethods;
    if (allMethods.length > 20) {
        // Fisher-Yates shuffle and take first 20
        for (let i = allMethods.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [allMethods[i], allMethods[j]] = [allMethods[j], allMethods[i]];
        }
        selectedMethods = allMethods.slice(0, 20);
    }
    
    // If we don't have enough methods, expand the variance and try again
    if (selectedMethods.length < 20 && variance < 40) { // Limit recursion
        console.log(`⚠️ Only found ${selectedMethods.length} methods. Trying with expanded variance...`);
        // Recursively call with greater variance
        return processRepositories(directories, outputCsv, targetLines, variance + 10);
    }

    // Write results to CSV
    if (selectedMethods.length > 0) {
        data.push(...selectedMethods);
        
        const csvWriter = csv({
            path: outputCsv,
            header: [
                {id: 'fullyQualifiedName', title: 'Fully Qualified Name'},
                {id: 'filePath', title: 'File Path'},
                {id: 'methodName', title: 'Method Name'},
                {id: 'methodBody', title: 'Method Body'},
                {id: 'lineCount', title: 'Line Count'}
            ]
        });
        
        const records = selectedMethods.map(method => ({
            fullyQualifiedName: method[0],
            filePath: method[1],
            methodName: method[2],
            methodBody: method[3],
            lineCount: method[4]
        }));
        
        csvWriter.writeRecords(records)
            .then(() => {
                console.log(`✅ CSV generated: ${outputCsv}`);
                console.log(`✅ Processed ${filesProcessed} files, skipped ${skippedFiles} files`);
                console.log(`✅ Found ${allMethods.length} methods in target range, wrote ${selectedMethods.length} to CSV.`);
            });
    } else {
        console.log(`⚠️ No methods found with ${targetLines}±${variance} lines. Try adjusting the target or variance.`);
    }
    
    return selectedMethods.length;
}

// Main execution
if (require.main === module) {
    const repositories = [
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/javaScript/javascript-algorithms",
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/javaScript/node",
        "/Users/durjoy/Documents/Lab CSSE/Github_repos/javaScript/react"
    ];
    
    processRepositories(
        repositories, 
        "/Users/durjoy/Documents/Lab CSSE/NamingRefactoring/Result_files/JavaScript/random_methods_javascript.csv", 
        targetLines = 50, 
        variance = 20
    );
}

module.exports = {
    extractMethodBody,
    countNonCommentLines,
    isTestMethod,
    findMethods,
    processRepositories
}; 