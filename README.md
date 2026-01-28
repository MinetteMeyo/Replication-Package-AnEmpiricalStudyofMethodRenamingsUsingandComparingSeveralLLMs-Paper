NamingRefactoring
=================

This repository is a **research project** that evaluates the impact of large language models (LLMs) on method renaming tasks, with a current focus on **method renaming** across multiple programming languages (Java / Python / JavaScript).  

The overall workflow is:

- **Define refactoring task types**: method renaming from legacy code base.
- **Extract methods from real GitHub projects** (multi-language AST / parser–based extraction).
- **Query multiple LLMs for renaming suggestions**.
- **Analyze the results** 

---

Repository Structure
--------------------

- `GitHubRepoSelection/`  
  - Contains the notebook `Github repo selection.ipynb`.  
  - Used to select candidate GitHub repositories by language (Java / Python / JavaScript), with filters on stars, forks, project size, and heuristics to exclude tutorial / documentation repositories.

- `MethodExtraction/`  
  - **Core code directory** that extracts methods from the selected repositories and calls LLMs for method name suggestions.  
  - It is organized by language :
    - **Python**: e.g. `Python/main.py`  
      - Uses the built‑in Python `ast` module for AST parsing.  
      - Filters methods by length (target ≈ 50 lines with ±20 line tolerance), skipping test methods and magic methods.  
      - LLM caller scripts: `LLMApiCallGpt.py`, `LLMApiCallClaude.py`, `LLMApiCallLlama.py`, etc.  
    - **JavaScript**: e.g. `JavaScript/javascript_method_parser.js`  
      - Uses Acorn JS parser to extract function declarations, function expressions, arrow functions, and class methods.  
      - Name suggestion scripts: `gpt4o_method_name_suggester.js`, `claude_method_name_suggester.js`, `llama_method_name_suggester.js`.  
    - **Java**: e.g. `Java/JavaMethodExtractor.java`  
      - Uses ANTLR4 + a Java 20 grammar for parsing and method extraction.  
      - Name suggestion implementations: `JavaMethodNameSuggester.java`, `JavaMethodNameSuggesterClaude.java`, `JavaMethodNameSuggesterLLaMA.java`.

- `ResultFiles/`  
  - Stores CSV outputs for extracted methods and LLM suggestions, split into language‑specific subdirectories: `Java/`, `JavaScript/`, `Python/`.  
  - For each language you typically find:
    - `random_methods_[language].csv`: random sample of target methods (columns usually include: Fully Qualified Name, File Path, Method Name, Method Body, Line Count, etc.).  
    - `[llm]_suggestedMethodNames_[language].csv`: LLM name suggestions (adds context token counts, context snippets, and one or more suggested names).  
  - LLMs currently used include **GPT‑4o, Claude (Sonnet), LLaMA (Llama‑4‑Maverick)** and similar.

- `Algorithm/` and `AnalyzingData/`  
  -  
  - 

---

Workflow / How to Use
---------------------

> Note: This is research code. Several scripts contain **hard‑coded paths and API keys**. Before reproducing any experiments, adapt these values to your environment.

### 1. Environment Setup

- **Core software**
  - Python 3 (3.9+ recommended) with dependencies such as `openai`, `anthropic`, `tiktoken`, `requests`, etc.
  - Node.js (≥ 14 recommended) for JavaScript parsing and JS‑based LLM client scripts.
  - Java (JDK and Maven) for Java method extraction and LLM clients.

- **External services / API keys**
  - OpenAI (for GPT‑4o and related models).
  - Anthropic (for Claude models).
  - TogetherAI or other providers exposing LLaMA‑family models.


### 2. Selecting GitHub Repositories

- Open and run `GitHubRepoSelection/Github repo selection.ipynb`.  
- Configure and execute the notebook to select repositories that satisfy the constraints (language, stars, forks, size, etc.).  
- Clone the selected repositories locally to a directory that matches the hard‑coded or configured paths used by the extraction scripts.

### 3. Method Extraction

Once the target language repositories are cloned locally, run the language‑specific extraction scripts:

- **Python method extraction**
  - Go to `MethodExtraction/Python/`.  
  - Configure the code root directory (many scripts assume something like `/Users/durjoy/Documents/Lab CSSE/Github_repos/`; you should change this to your own path).  
  - Run:

    ```bash
    python main.py
    ```

- **JavaScript method extraction**
  - Go to `MethodExtraction/JavaScript/`.  
  - Install dependencies:

    ```bash
    npm install
    ```

  - Adjust the code root path in the script if necessary, then run:

    ```bash
    node javascript_method_parser.js
    ```

- **Java method extraction**
  - Go to `MethodExtraction/Java/` (or the corresponding Maven module).  
  - Ensure ANTLR4 and Maven configuration are correct, then compile and run:

    ```bash
    mvn compile
    mvn exec:java -Dexec.mainClass="...JavaMethodExtractor"   # set mainClass according to your actual project config
    ```

For all languages, the extraction scripts apply a line‑count filter (≈ 50 lines ± 20) and write results to `ResultFiles/[Language]/random_methods_[language].csv`.

### 4. Generating LLM Method Name Suggestions

After extraction, invoke the language‑ and model‑specific scripts to generate name suggestions. Typical scripts include:

- **Python**
  - `LLMApiCallGpt.py`
  - `LLMApiCallClaude.py`
  - `LLMApiCallLlama.py`

- **JavaScript**
  - `gpt4o_method_name_suggester.js`
  - `claude_method_name_suggester.js`
  - `llama_method_name_suggester.js`

- **Java**
  - `JavaMethodNameSuggester.java`
  - `JavaMethodNameSuggesterClaude.java`
  - `JavaMethodNameSuggesterLLaMA.java`

Before running these scripts:

- Make sure the required API keys are available (environment variables or config files).  
- Update any input CSV paths so they point to `ResultFiles/[Language]/random_methods_[language].csv`.  

Each script writes its results to `ResultFiles/[Language]/[llm]_suggestedMethodNames_[language].csv`.

---

Result Files
------------

**1. `random_methods_[language].csv`**

- Produced by the method extraction scripts.  
- Typical columns:
  - `Fully Qualified Name`: fully qualified method name (including class and package / namespace).  
  - `File Path`: relative path to the source file.  
  - `Method Name`: original method name.  
  - `Method Body`: the method body as multi‑line code text.  
  - `Line Count`: number of lines in the method.  

**2. `[llm]_suggestedMethodNames_[language].csv`**

- Produced by the LLM‑based name suggestion scripts.  
- In addition to the method information above, it usually adds:
  - `Context Tokens`: number of tokens in the prompt context (for controlling length / model limits).  
  - `Context`: the code context fed to the LLM (e.g. surrounding code in addition to the method body).  
  - `Suggested Names` / `Top-k Names`: one or more candidate names generated by the model.  

These CSVs are then used for:

- Comparing naming quality across different models.  
- Comparing LLM suggestions with original names (e.g. readability or similarity).  
- Studying differences across languages and project types.

---

Important Notes
---------------

- **Hard‑coded paths**  
  - Several scripts use absolute paths like `/Users/durjoy/Documents/Lab CSSE/Github_repos/` and `/Users/durjoy/Documents/Lab CSSE/Result_files/`.  
  - Before running in a different environment, unify these to the correct local paths or refactor them into configurable parameters.


---

Contributing
------------

Contributions are welcome, especially in the following areas:

- Adding support for more languages or parsers.  
- Integrating additional LLM providers or model variants.  
- Implementing and refining analysis scripts (RQ1/RQ2/RQ3).  
- Improving configuration (removing hard‑coded paths and secrets, making pipelines more reproducible).  

You can open Issues or submit Pull Requests to propose improvements and extensions.
