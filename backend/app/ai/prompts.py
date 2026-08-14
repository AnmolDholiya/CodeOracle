"""Centralized prompt templates for CodeOracle AI Services."""

AI_TRUTH_GUARD_INSTRUCTION = (
    "CRITICAL MANDATE: Only describe behavior supported by the supplied source code and analysis context. "
    "Keep explanations ultra-concise, brief, direct, and under 80 words. Prefer short bullet points. "
    "Do NOT repeat source code."
)

SYSTEM_PROMPT_CODEORACLE = (
    "You are CodeOracle AI, a senior software architect and legacy codebase explainer. "
    f"{AI_TRUTH_GUARD_INSTRUCTION}"
)

def build_test_explanation_prompt(code_snippet: str) -> str:
    """Builds a simple test prompt to explain a short code snippet."""
    return (
        f"Briefly explain what the following Python code does in 1 concise sentence:\n\n"
        f"```python\n{code_snippet[:500]}\n```\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_project_explanation_prompt(
    total_files: int,
    total_loc: int,
    file_list: list,
    ast_summary: dict,
    dep_summary: dict,
    ext_libs: list
) -> str:
    """Builds compact prompt for project-level architectural overview."""
    file_basenames = [f.split("/")[-1] for f in file_list[:12]]
    ext_names = [lib.get('name') for lib in ext_libs[:6]]
    
    return (
        f"Generate a concise architectural project explanation for this codebase based on static analysis data.\n\n"
        f"Metrics: {total_files} files, {total_loc} LOC.\n"
        f"Key Files: {file_basenames}\n"
        f"AST Metrics: {ast_summary}\n"
        f"External Libraries: {ext_names}\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- purpose: 1 short sentence summary\n"
        f"- architecture: 1 short sentence design pattern summary\n"
        f"- major_modules: top 3 key files\n"
        f"- important_dependencies: key external libraries\n"
        f"- execution_flow: 2 short bullet points\n"
        f"- maintenance_concerns: 1 short bullet point\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_module_explanation_prompt(
    file_path: str,
    source_code: str,
    file_ast_info: dict,
    file_dep_info: dict
) -> str:
    """Builds compact prompt for Python file/module level explanation."""
    classes_list = [c.get('name') for c in file_ast_info.get('classes', [])[:5]]
    functions_list = [fn.get('name') for fn in file_ast_info.get('functions', [])[:8]]

    return (
        f"Analyze the Python module '{file_path}' and provide a concise structured explanation.\n\n"
        f"File Path: {file_path}\n"
        f"AST Symbols: classes={classes_list}, functions={functions_list}\n"
        f"Source Code Snippet:\n"
        f"```python\n{source_code[:1000]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- file_path: '{file_path}'\n"
        f"- purpose: 1 short sentence purpose\n"
        f"- summary: 1 line summary\n"
        f"- responsibilities: 2 short bullet points\n"
        f"- dependencies: key imports\n"
        f"- classes: class names\n"
        f"- functions: function names\n"
        f"- potential_issues: 1 short bullet point\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_markdown_explanation_prompt(file_path: str, content: str) -> str:
    """Builds compact prompt for Markdown (.md) documentation explanation."""
    return (
        f"Analyze the Markdown document '{file_path}' and provide a concise structured explanation.\n\n"
        f"File Path: {file_path}\n"
        f"Content Snippet:\n"
        f"```markdown\n{content[:1000]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- file_path: '{file_path}'\n"
        f"- purpose: 1 short sentence document purpose\n"
        f"- summary: 1 line summary\n"
        f"- responsibilities: 2 key topic summaries\n"
        f"- dependencies: mentioned technologies or APIs\n"
        f"- classes: []\n"
        f"- functions: []\n"
        f"- potential_issues: []\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_json_config_explanation_prompt(file_path: str, content: str, file_type: str) -> str:
    """Builds compact prompt for JSON or Configuration files."""
    return (
        f"Analyze the {file_type.upper()} config file '{file_path}' and provide a concise structured explanation.\n\n"
        f"File Path: {file_path}\n"
        f"Content Snippet:\n"
        f"```\n{content[:1000]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- file_path: '{file_path}'\n"
        f"- purpose: 1 short sentence configuration purpose\n"
        f"- summary: 1 line summary\n"
        f"- responsibilities: 2 key config section summaries\n"
        f"- dependencies: external URLs or package references\n"
        f"- classes: []\n"
        f"- functions: []\n"
        f"- potential_issues: []\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_js_ts_explanation_prompt(file_path: str, content: str, file_type: str) -> str:
    """Builds compact prompt for JavaScript / TypeScript files."""
    return (
        f"Analyze the {file_type.upper()} source file '{file_path}' and provide a concise structured explanation.\n\n"
        f"File Path: {file_path}\n"
        f"Source Code Snippet:\n"
        f"```javascript\n{content[:1000]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- file_path: '{file_path}'\n"
        f"- purpose: 1 short sentence purpose\n"
        f"- summary: 1 line summary\n"
        f"- responsibilities: 2 short bullet points\n"
        f"- dependencies: imported packages\n"
        f"- classes: class names if any\n"
        f"- functions: function or component names\n"
        f"- potential_issues: 1 short bullet point\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_generic_text_explanation_prompt(file_path: str, content: str, file_type: str) -> str:
    """Builds generic text file explanation prompt."""
    return (
        f"Analyze the text file '{file_path}' ({file_type}) and provide a concise structured explanation.\n\n"
        f"File Path: {file_path}\n"
        f"Content Snippet:\n"
        f"```\n{content[:1000]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- file_path: '{file_path}'\n"
        f"- purpose: 1 short sentence purpose\n"
        f"- summary: 1 line summary\n"
        f"- responsibilities: 2 short bullet points\n"
        f"- dependencies: []\n"
        f"- classes: []\n"
        f"- functions: []\n"
        f"- potential_issues: []\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_class_explanation_prompt(
    file_path: str,
    class_name: str,
    class_source: str,
    class_ast_info: dict
) -> str:
    """Builds compact prompt for class-level explanation."""
    return (
        f"Analyze the Python class '{class_name}' located in '{file_path}' and provide a concise explanation.\n\n"
        f"Class: {class_name}\n"
        f"Methods: {[m.get('name') for m in class_ast_info.get('methods', [])[:5]]}\n"
        f"Source Code Snippet:\n"
        f"```python\n{class_source[:800]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- class_name: '{class_name}'\n"
        f"- purpose: 1 short sentence purpose\n"
        f"- responsibilities: 2 short bullet points\n"
        f"- constructor_summary: 1 short sentence\n"
        f"- important_methods: key method names\n"
        f"- inheritance: base classes\n"
        f"- dependencies: imported classes\n"
        f"- potential_issues: []\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )

def build_function_explanation_prompt(
    file_path: str,
    function_name: str,
    function_source: str,
    function_ast_info: dict
) -> str:
    """Builds compact prompt for function/method level explanation."""
    params = [p.get('name') for p in function_ast_info.get('parameters', [])[:5]]
    return (
        f"Analyze the Python function '{function_name}' in '{file_path}' and provide a concise explanation.\n\n"
        f"Function: {function_name}({', '.join(params)})\n"
        f"Calls: {function_ast_info.get('calls', [])[:4]}\n"
        f"Source Code Snippet:\n"
        f"```python\n{function_source[:800]}\n```\n\n"
        f"Provide a structured JSON object containing:\n"
        f"- function_name: '{function_name}'\n"
        f"- purpose: 1 short sentence purpose\n"
        f"- parameters_explained: Array of {{ 'name': param_name, 'explanation': 1 line description }}\n"
        f"- return_value_explained: 1 short sentence return value description\n"
        f"- step_by_step_logic: 2-3 short step bullet points\n"
        f"- calls: called function names\n"
        f"- dependencies: key modules\n"
        f"- side_effects: []\n"
        f"- edge_cases: 1 short note\n"
        f"- potential_issues: []\n\n"
        f"{AI_TRUTH_GUARD_INSTRUCTION}"
    )
