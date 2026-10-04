import os
import io
import sys
import ast
import json
import re
from typing import Tuple
import streamlit as st
from groq import Groq

# --- Page Configuration & Styling ---
st.set_page_config(
    page_title="Multi-Agent Code Engine",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern design
st.markdown("""
<style>
    /* Metric Cards Styling */
    .metric-card {
        background-color: #1E222D;
        border: 1px solid #2E3440;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .metric-card h3 {
        color: #88C0D0;
        margin: 0 0 5px 0;
        font-size: 1.8rem;
    }
    .metric-card p {
        color: #D8DEE9;
        margin: 0;
        font-size: 0.9rem;
        font-weight: 500;
    }
    /* Agent Step Badges */
    .agent-header {
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 15px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- Core Engine Logic ---

class SecurityException(Exception): 
    pass

class CodeSecurityValidator(ast.NodeVisitor):
    FORBIDDEN_MODULES = {'os', 'subprocess', 'sys', 'shutil', 'socket'}
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split('.')[0] in self.FORBIDDEN_MODULES:
                raise SecurityException(f"Forbidden module import: '{alias.name}'")
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in self.FORBIDDEN_MODULES:
            raise SecurityException(f"Forbidden module import: '{node.module}'")
        self.generic_visit(node)

class IsolatedPythonExecutor:
    def validate_code_safety(self, code_str: str):
        tree = ast.parse(code_str)
        validator = CodeSecurityValidator()
        validator.visit(tree)

    def run(self, code_str: str):
        clean_code = code_str.replace("```python", "").replace("```", "").strip()
        try:
            self.validate_code_safety(clean_code)
        except SecurityException as sec_err:
            return False, f"Security Validation Failed: {sec_err}"
        except Exception as parse_err:
            return False, f"Syntax/Parsing Error: {parse_err}"

        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        try:
            exec_globals = {}
            exec(clean_code, exec_globals)
            output = redirected_output.getvalue()
            return True, output if output else "Code executed successfully (no output)."
        except Exception as e:
            return False, f"Runtime Exception: {str(e)}"
        finally:
            sys.stdout = old_stdout

class MultiAgentOrchestrator:
    def __init__(self, api_key: str, model_id: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model_id = model_id
        self.executor = IsolatedPythonExecutor()

    def _invoke_llm(self, system_instruction: str, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content

    def synthesize_code(self, task: str, critique: str = None) -> str:
        sys_directive = (
            "You are a Senior Software Engineer. Output clean, executable Python code "
            "wrapped inside ```python code block ``` without markdown introductions or commentary."
        )
        prompt = f"Target Task: {task}"
        if critique:
            prompt += f"\nPrevious attempt failed. Adjust code based on feedback:\n{critique}"
        return self._invoke_llm(sys_directive, prompt)

    def evaluate_output(self, task: str, code: str, logs: str) -> Tuple[bool, str]:
        sys_directive = (
            "You are a Code Reviewer. Analyze code and execution output against requirements. "
            'Output valid JSON formatted strictly as: {"passed": boolean, "analysis": "string"}'
        )
        prompt = f"Task: {task}\nCode:\n{code}\nExecution Output:\n{logs}"
        raw_eval = self._invoke_llm(sys_directive, prompt)
        try:
            clean_json = re.sub(r"^```json\s*|
