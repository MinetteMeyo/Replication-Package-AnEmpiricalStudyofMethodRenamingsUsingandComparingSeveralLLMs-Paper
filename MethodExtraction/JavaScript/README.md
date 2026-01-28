# JavaScript Method Parser

A JavaScript tool that uses the Acorn parser to extract methods from JavaScript codebases, similar to the Python method parser. This tool analyzes JavaScript repositories and extracts methods that match specific line count criteria.

## Features

- **AST-based parsing**: Uses Acorn parser for accurate JavaScript code analysis
- **Multiple function types**: Supports FunctionDeclaration, FunctionExpression, ArrowFunctionExpression, and MethodDefinition
- **Comment filtering**: Excludes comments and blank lines from line count
- **Test method detection**: Automatically skips test methods and files
- **Random selection**: Selects up to 20 random methods from the found matches
- **CSV output**: Generates structured CSV files with method information
- **Recursive variance**: Automatically expands search criteria if not enough methods are found

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
npm install
```

## Usage

### Basic Usage

```bash
node javascript_method_parser.js
```

### Custom Configuration

Edit the repositories array in `javascript_method_parser.js`:

```javascript
const repositories = [
    "/path/to/your/javascript/repo1",
    "/path/to/your/javascript/repo2",
    "/path/to/your/javascript/repo3"
];

processRepositories(
    repositories, 
    "/path/to/output/random_methods_javascript.csv", 
    targetLines = 50,  // Target line count
    variance = 20      // Acceptable variance (±20 lines)
);
```

### Programmatic Usage

```javascript
const { processRepositories } = require('./javascript_method_parser');

const repositories = ['/path/to/repo1', '/path/to/repo2'];
const outputPath = '/path/to/output.csv';

processRepositories(repositories, outputPath, 50, 20);
```

## Output Format

The tool generates a CSV file with the following columns:

- **Fully Qualified Name**: Module name and method name (e.g., `module::methodName`)
- **File Path**: Full path to the source file
- **Method Name**: Name of the method/function
- **Method Body**: Complete source code of the method
- **Line Count**: Number of non-comment, non-blank lines

## Supported JavaScript Constructs

- Function declarations: `function myFunction() {}`
- Function expressions: `const myFunction = function() {}`
- Arrow functions: `const myFunction = () => {}`
- Method definitions: `class MyClass { myMethod() {} }`
- Object methods: `const obj = { method() {} }`

## Configuration Options

- **targetLines**: Target number of lines for methods (default: 50)
- **variance**: Acceptable range around target lines (default: ±20)
- **file size limit**: Skips files larger than 1MB
- **test detection**: Automatically skips methods with 'test' in name or path

## Dependencies

- **acorn**: JavaScript parser for AST generation
- **csv-writer**: CSV file generation
- **fs**: File system operations (Node.js built-in)
- **path**: Path manipulation (Node.js built-in)

## Requirements

- Node.js >= 14.0.0
- npm or yarn package manager

## Example Output

```csv
Fully Qualified Name,File Path,Method Name,Method Body,Line Count
utils::formatData,/path/to/utils.js,formatData,"function formatData(data) {
    if (!data) return null;
    return data.map(item => ({
        id: item.id,
        name: item.name.toUpperCase(),
        timestamp: new Date(item.created_at)
    }));
}",8
```

## Error Handling

The tool includes comprehensive error handling:
- Skips files that can't be parsed
- Handles missing directories gracefully
- Continues processing even if individual files fail
- Provides detailed logging of skipped files and errors

## License

MIT License 