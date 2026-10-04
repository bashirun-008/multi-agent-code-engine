Markdown
# Multi-Agent Code Engine

An autonomous 3-agent software engineering framework (**Architect**, **Executor**, **Reviewer**) built with Python and Groq (`llama-3.3-70b-versatile`). The system iteratively generates code, executes it, captures runtime output or errors, and feeds execution feedback back into the LLM context for automatic self-correction.

---

## 🏗️ Architecture & Workflow

Given a natural-language task, the system processes it through a self-correcting 3-role pipeline (up to 4 iterations):

+-----------------+      +-------------------+      +------------------+
|   1. Architect  | ---> |    2. Executor    | ---> |   3. Reviewer    |
| (Generates Code)|      | (Runs Code/AST)   |      | (Pass/Fail Gate) |
+-----------------+      +-------------------+      +------------------+
^                                                    |
|                  Feedback / Error Loop             | (If Fail /
+----------------------------------------------------+  Error)


1. **Architect**: Generates a Python solution using Groq's `llama-3.3-70b-versatile`.
2. **Executor**: Runs the generated code using Python's `exec()` in-process and captures `stdout` or runtime exception tracebacks.
3. **Reviewer**: An LLM call evaluated via Pydantic structured output that judges whether the code and output satisfy the task requirements, returning a structured pass/fail verdict with detailed reasoning.

If execution fails or the Reviewer rejects the solution, the error log and feedback are appended back to the Architect's context for another attempt until it passes or retries are exhausted.

---

## 🔒 Safety & Execution Design

* **AST Import Validator**: Performs static code analysis using Python's `ast` module to block a list of restricted modules (`os`, `subprocess`, `sys`, `shutil`, `socket`) prior to execution.
* **Current Boundary**: This is an import check, not a full sandbox. Code runs in the same process without strict CPU/memory limits or restrictions on standard file operations (e.g., `open()`). Real isolation (e.g., containerized execution) is planned for future iterations.

---

## 🛠️ Tech Stack

* **Language**: Python (Jupyter Notebook / Google Colab)
* **LLM Provider**: Groq API (`llama-3.3-70b-versatile`)
* **Static Analysis**: Standard library `ast` module
* **Structured Output**: Pydantic

---

## 🧪 Tested Tasks

* [x] Generating a Fibonacci sequence function
* [x] Palindrome string checking

Both tasks successfully converged to passing solutions within the self-correction retry loop.

---

## 🚀 How to Run

1. **Get an API Key**: Obtain a Groq API key from [console.groq.com](https://console.groq.com).
2. **Configure Environment**:
   * Open `model1.ipynb` in Google Colab.
   * Add your API key to Colab Secrets (**Colab** → **Secrets** panel) under the name `GROQ_API_KEY`.
3. **Execute**:
   * Run all notebook cells.
   * Invoke the agent pipeline with your task prompt:


# Example Usage
prompt = "Write a Python function to check if a string is a palindrome."
result = run_code_engine(prompt)
print(result)
📌 Limitations & Roadmap
[ ] Containerized Execution: Upgrade the executor to use Docker or subprocess isolation to enforce CPU/memory limits and true sandboxing.

[ ] Complex Benchmarks: Test multi-file, multi-step, or ambiguous software engineering tasks.

[ ] Persistence: Add persistent logging for past attempts and execution history across runs.

[ ] Code Cleanup: Consolidate duplicate notebook cells from iterative editing.

👤 Author
Md Bashirun Sultan
