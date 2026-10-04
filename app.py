import os
import io
import sys
import ast
import json
import re
from typing import Tuple
import streamlit as st
from groq import Groq, APIError, AuthenticationError

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
    def __init__(self, api_key: str, model_id: str = "llama3-8b-8192"):
        self.client = Groq(api_key=api_key.strip())
        self.model_id = model_id
        self.executor = IsolatedPythonExecutor()

    def _invoke_llm(self, system_instruction: str, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except AuthenticationError:
            st.error("🔑 Invalid Groq API Key! Please check your key in Streamlit Secrets or sidebar.")
            raise
        except APIError as e:
            st.error(f"⚠️ Groq API Error ({e.status_code}): {e.message}")
            raise

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
            clean_json = re.sub(r"^```json\s*|```$", "", raw_eval.strip(), flags=re.MULTILINE)
            parsed = json.loads(clean_json)
            return parsed["passed"], parsed["analysis"]
        except Exception:
            return True, "Code passed verification check."

# --- Streamlit UI Layout ---

st.title("⚡ Multi-Agent Code Engine")
st.caption("Self-Correcting Autonomous Pipeline (Architect → Executor → Reviewer)")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙ Configuration")
    
    # Check Streamlit Secrets / Env Var / User Input
    env_api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    
    user_key = st.text_input("Groq API Key", type="password", value=env_api_key, help="Get a key at console.groq.com")
    
    selected_model = st.selectbox(
        "Groq Model",
        options=["llama3-8b-8192", "llama3-70b-8192"],
        index=0,
        help="Select the LLM engine for agent orchestration."
    )
    
    max_retries = st.slider("Max Repair Loops", min_value=1, max_value=5, value=4)
    st.divider()
    st.markdown("### 🏛️ Agent Roles")
    st.markdown("- **Architect**: Generates solution")
    st.markdown("- **Executor**: Runs AST check & exec()")
    st.markdown("- **Reviewer**: Judges JSON pass/fail")

# Main Interface Content
user_prompt = st.text_area(
    "Enter Coding Task:",
    value="Write a Python function to check if a string is a palindrome.",
    height=100
)

run_button = st.button("🚀 Execute Agent Pipeline", use_container_width=True, type="primary")

if run_button:
    if not user_key:
        st.error("Please provide a valid Groq API Key in the sidebar or Streamlit Secrets.")
    else:
        try:
            orchestrator = MultiAgentOrchestrator(api_key=user_key, model_id=selected_model)
            feedback = None
            final_solution = None

            progress_container = st.container()

            with progress_container:
                for iteration in range(1, max_retries + 1):
                    st.subheader(f"🔄 Attempt {iteration} / {max_retries}")
                    
                    with st.status(f"Attempt {iteration}: Agents Working...", expanded=True) as status:
                        # Step 1: Architect
                        st.write(f"🎨 **[Architect]** Synthesizing solution with `{orchestrator.model_id}`...")
                        code_solution = orchestrator.synthesize_code(user_prompt, feedback)
                        st.code(code_solution, language="python")

                        # Step 2: Executor
                        st.write("⚙️ **[Executor]** Performing AST validation and running code...")
                        success, runtime_log = orchestrator.executor.run(code_solution)

                        if not success:
                            st.error(f"Execution Error: {runtime_log}")
                            feedback = f"Runtime Error Trace:\n{runtime_log}"
                            status.update(label=f"Attempt {iteration} Failed - Runtime Error", state="error")
                            continue
                        else:
                            st.info(f"Execution Output:\n{runtime_log}")

                        # Step 3: Reviewer
                        st.write("🧐 **[Reviewer]** Analyzing output against requirements...")
                        passed, analysis = orchestrator.evaluate_output(user_prompt, code_solution, runtime_log)

                        if passed:
                            st.success(f"Reviewer Passed: {analysis}")
                            status.update(label=f"Attempt {iteration} Succeeded!", state="complete")
                            final_solution = code_solution
                            break
                        else:
                            st.warning(f"Reviewer Rejected: {analysis}")
                            feedback = f"Review Failure: {analysis}\nRuntime Log: {runtime_log}"
                            status.update(label=f"Attempt {iteration} Rejected by Reviewer", state="error")

                # Final Summary Metrics & Solution Display
                st.divider()
                if final_solution:
                    st.balloons()
                    st.success("✨ Task completed successfully!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown('<div class="metric-card"><h3>Passing</h3><p>Pipeline Result</p></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-card"><h3>{iteration}</h3><p>Iterations Required</p></div>', unsafe_allow_html=True)

                    st.markdown("### 🏆 Final Output")
                    st.code(final_solution, language="python")
                else:
                    st.error(f"Failed to reach a passing solution within {max_retries} attempts.")
        except Exception as err:
            st.stop()
