Multi-Agent Code Engine
A self-correcting code generation pipeline where three LLM-driven roles — Architect, Executor, and Reviewer — collaborate to generate, run, and iteratively fix Python code for a given task.
Overview
Given a natural-language task, the system:
Architect — generates a Python solution using Groq's Llama-3.3-70B
Executor — runs the generated code, capturing output or runtime errors
Reviewer — an LLM call that judges whether the code and its output actually satisfy the task, returning a pass/fail verdict with reasoning
If execution fails or the Reviewer rejects the solution, the error/feedback is fed back into the Architect for another attempt — up to 4 iterations — until the code passes or retries are exhausted.
How It's Actually Implemented
LLM backend: Groq API, llama-3.3-70b-versatile
Code execution: Python's exec(), run in-process with stdout captured
Safety check: an AST-based import validator blocks a fixed list of modules (os, subprocess, sys, shutil, socket) before execution. This is an import restriction, not a true sandbox — code still runs in the same process with no resource limits (memory, CPU time, infinite loops) or restrictions on other risky operations like file I/O via open(). Real isolation would require running generated code in a separate process or container.
Review step: a second LLM call evaluates the code + execution output against the original task and returns a structured pass/fail judgment.
Tested On
Generating a Fibonacci sequence function
Checking whether a string is a palindrome
Both tasks completed successfully within the retry loop. The system hasn't yet been tested on more complex, multi-step, or ambiguous engineering tasks.
Tech Stack
Python
Groq API (Llama-3.3-70B)
ast module for static code analysis
Pydantic (for structured review output schema)
Known Limitations / Next Steps
Execution is not truly sandboxed — moving to subprocess isolation or a containerized executor (e.g., Docker) would meaningfully improve safety
Only tested on small, well-defined algorithmic tasks so far — needs testing on harder, multi-file, or ambiguous tasks to see how well the retry loop handles real complexity
Notebook has some duplicated code from iterative editing that should be cleaned up
No persistent logging of past runs/attempts — each run is independent
How to Run
Get a Groq API key from console.groq.com
In Colab, add it as a secret named GROQ_API_KEY (Colab → Secrets panel)
Run all cells, then call:
Python
Author
Md Bashirun Sultana
