import os
import json
import time
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple

from app.ai import get_ai_provider
from app.schemas.improvements import (
    EvidenceItem,
    ImprovementRecommendation,
    ProjectHealthMetrics,
    AccomplishmentItem,
    ProjectImprovementsResponse,
    AIImprovementResponseModel,
    AIRecommendationItem
)
from app.schemas.ast import ProjectAnalysisResponse, ASTFileAnalysis
from app.schemas.dependency import DependencyGraphResponse
from app.schemas.project import ProjectMetadata
from app.services.extractor import get_project_directory
from app.services.python_ast import analyze_project_workspace
from app.services.dependency_graph import generate_dependency_graph
from app.services.code_smell_service import analyze_code_smells

# In-flight request lock for AI improvement explanations
_IN_FLIGHT_AI_REQUESTS: Dict[str, asyncio.Task] = {}

def _read_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def _write_json_file(file_path: str, data: Any):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            if hasattr(data, "model_dump_json"):
                f.write(data.model_dump_json(indent=2))
            else:
                json.dump(data, f, indent=2)
    except Exception:
        pass


def compute_deterministic_improvements(project_id: str) -> ProjectImprovementsResponse:
    """
    Deterministic Local Evidence Engine:
    Examines AST metadata, dependency graph, code smells, test results, and file metrics
    to produce verified improvement recommendations without calling external AI.
    """
    project_dir = get_project_directory(project_id)

    # 1. Load cached Project Metadata, AST Analysis, and Dependency Graph
    meta_dict = _read_json_file(os.path.join(project_dir, "project_metadata.json"))
    ast_dict = _read_json_file(os.path.join(project_dir, "analysis_ast.json"))
    dep_dict = _read_json_file(os.path.join(project_dir, "dependency_graph.json"))
    cache_dict = _read_json_file(os.path.join(project_dir, "explanation_cache.json")) or {}

    if ast_dict:
        try:
            ast_analysis = ProjectAnalysisResponse(**ast_dict)
        except Exception:
            ast_analysis = analyze_project_workspace(project_dir, project_id)
    else:
        ast_analysis = analyze_project_workspace(project_dir, project_id)

    if dep_dict:
        try:
            dep_graph = DependencyGraphResponse(**dep_dict)
        except Exception:
            dep_graph = generate_dependency_graph(ast_analysis)
    else:
        dep_graph = generate_dependency_graph(ast_analysis)

    total_files = len(ast_analysis.files_analyzed)
    total_loc = ast_analysis.total_lines_of_code

    # 2. Gather Verified Accomplishments ("What's Already Good")
    accomplishments: List[AccomplishmentItem] = []
    
    if total_files > 0:
        accomplishments.append(AccomplishmentItem(
            id="acc_ast_indexed",
            title="Static AST Indexed",
            detail=f"{total_files} source files with {total_loc:,} lines of code parsed without AI token cost.",
            category="INDEXING"
        ))

    # Check syntax errors
    syntax_error_files = [f.relative_path for f in ast_analysis.files_analyzed if f.has_syntax_error]
    if len(syntax_error_files) == 0 and total_files > 0:
        accomplishments.append(AccomplishmentItem(
            id="acc_syntax_clean",
            title="Clean Syntax",
            detail="100% of analyzed codebase files have valid, parseable syntax.",
            category="SYNTAX"
        ))

    # Check dependency graph connectivity
    if dep_graph.total_edges > 0:
        accomplishments.append(AccomplishmentItem(
            id="acc_deps_connected",
            title="Architecture Graph Analyzed",
            detail=f"{dep_graph.total_nodes} modules connected via {dep_graph.total_edges} verified dependency edges.",
            category="ARCHITECTURE"
        ))

    # Check test results if available in cache
    test_cache = cache_dict.get("tests", {})
    coverage_cache = cache_dict.get("coverage", {})
    
    if test_cache and test_cache.get("passed", 0) > 0:
        passed_count = test_cache.get("passed", 0)
        total_tests = test_cache.get("total", 0)
        accomplishments.append(AccomplishmentItem(
            id="acc_tests_passing",
            title="Automated Test Suite Verified",
            detail=f"{passed_count} of {total_tests} automated tests executed and passed.",
            category="TESTING"
        ))

    if coverage_cache and coverage_cache.get("coverage_percentage") is not None:
        cov_pct = coverage_cache.get("coverage_percentage")
        if cov_pct >= 80:
            accomplishments.append(AccomplishmentItem(
                id="acc_high_coverage",
                title="High Statement Coverage",
                detail=f"Automated test suite validates {cov_pct}% of executable code statements.",
                category="COVERAGE"
            ))

    # 3. Evidence-Backed Improvement Analyzers
    recommendations: List[ImprovementRecommendation] = []
    all_evidence: List[EvidenceItem] = []
    rec_counter = 1

    # --- A. Large Functions Analysis (AST Metric) ---
    for file_ast in ast_analysis.files_analyzed:
        for fn in file_ast.functions:
            fn_loc = fn.lines_of_code or (fn.end_line - fn.start_line + 1 if fn.end_line and fn.start_line else 0)
            if fn_loc >= 40:
                ev_id = f"ev_fn_len_{rec_counter}"
                ev = EvidenceItem(
                    id=ev_id,
                    type="ast",
                    file=file_ast.relative_path,
                    symbol=fn.name,
                    line_number=fn.start_line,
                    metric="function_lines_of_code",
                    value=fn_loc,
                    details=f"Function '{fn.name}' spans {fn_loc} lines (lines {fn.start_line}-{fn.end_line})."
                )
                all_evidence.append(ev)

                severity = "high" if fn_loc > 80 else "medium"
                recommendations.append(ImprovementRecommendation(
                    id=f"rec_large_fn_{rec_counter}",
                    category="LARGE_FUNCTIONS",
                    title=f"Refactor oversized function `{fn.name}` ({fn_loc} LOC)",
                    severity=severity,
                    confidence=1.0,
                    description=f"Function `{fn.name}` in `{file_ast.relative_path}` is {fn_loc} lines long, exceeding recommended clean function length (30 LOC).",
                    why_it_matters="Long functions combine multiple responsibilities, increasing cognitive load, bug density, and testing difficulty.",
                    recommendation=f"Decompose `{fn.name}` into smaller, single-purpose helper functions with explicit inputs and outputs.",
                    affected_files=[file_ast.relative_path],
                    affected_symbols=[fn.name],
                    evidence=[ev],
                    source="static_analysis",
                    action=f"Extract sub-tasks inside `{fn.name}` into modular helpers.",
                    is_verified=True
                ))
                rec_counter += 1

    # --- B. Large Files Analysis ---
    for file_ast in ast_analysis.files_analyzed:
        if file_ast.lines_of_code >= 400:
            ev_id = f"ev_file_len_{rec_counter}"
            ev = EvidenceItem(
                id=ev_id,
                type="file_metric",
                file=file_ast.relative_path,
                symbol=None,
                line_number=1,
                metric="file_lines_of_code",
                value=file_ast.lines_of_code,
                details=f"File contains {file_ast.lines_of_code} non-empty lines of code."
            )
            all_evidence.append(ev)

            recommendations.append(ImprovementRecommendation(
                id=f"rec_large_file_{rec_counter}",
                category="LARGE_FILES",
                title=f"Split monolithic module `{file_ast.relative_path}` ({file_ast.lines_of_code} LOC)",
                severity="medium",
                confidence=1.0,
                description=f"`{file_ast.relative_path}` contains {file_ast.lines_of_code} lines of code.",
                why_it_matters="Monolithic files often violate the Single Responsibility Principle and create merge conflicts in collaborative codebases.",
                recommendation=f"Group related classes, handlers, or utilities into a package directory with submodules.",
                affected_files=[file_ast.relative_path],
                affected_symbols=[],
                evidence=[ev],
                source="static_analysis",
                action="Split file into domain-specific submodules.",
                is_verified=True
            ))
            rec_counter += 1

    # --- C. Code Smells: Deep Nesting & Parameter Count ---
    for file_ast in ast_analysis.files_analyzed:
        abs_path = file_ast.absolute_path or os.path.join(project_dir, file_ast.relative_path)
        if os.path.exists(abs_path) and file_ast.lines_of_code < 5000:
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                smells = analyze_code_smells(content)
                for smell in smells:
                    smell_type = smell.get("type", "")
                    if smell_type == "unused_import":
                        ev_id = f"ev_unused_imp_{rec_counter}"
                        ev = EvidenceItem(
                            id=ev_id,
                            type="code_smell",
                            file=file_ast.relative_path,
                            metric="unused_imports",
                            value=smell.get("description", ""),
                            details=smell.get("description", "")
                        )
                        all_evidence.append(ev)
                        recommendations.append(ImprovementRecommendation(
                            id=f"rec_unused_imp_{rec_counter}",
                            category="UNUSED_IMPORTS",
                            title=f"Remove unused imports in `{file_ast.relative_path}`",
                            severity="low",
                            confidence=1.0,
                            description=smell.get("description", "Unused imports detected."),
                            why_it_matters="Unused imports clutter module namespace and can introduce unnecessary startup import overhead.",
                            recommendation="Remove the unused import statements.",
                            affected_files=[file_ast.relative_path],
                            evidence=[ev],
                            source="static_analysis",
                            action="Clean up unused import headers.",
                            is_verified=True
                        ))
                        rec_counter += 1
                    elif smell_type == "excessive_nesting":
                        ev_id = f"ev_nesting_{rec_counter}"
                        ev = EvidenceItem(
                            id=ev_id,
                            type="code_smell",
                            file=file_ast.relative_path,
                            metric="nesting_depth",
                            value=smell.get("description", ""),
                            details=smell.get("description", "")
                        )
                        all_evidence.append(ev)
                        recommendations.append(ImprovementRecommendation(
                            id=f"rec_nesting_{rec_counter}",
                            category="COMPLEXITY",
                            title=f"Flatten deeply nested logic in `{file_ast.relative_path}`",
                            severity="medium",
                            confidence=1.0,
                            description=smell.get("description", "Deeply nested control structures detected."),
                            why_it_matters="Deep nesting makes conditional branches difficult to trace and error-prone.",
                            recommendation="Use guard clauses, early returns, or helper functions to reduce nesting depth.",
                            affected_files=[file_ast.relative_path],
                            evidence=[ev],
                            source="static_analysis",
                            action="Apply early return guard clauses.",
                            is_verified=True
                        ))
                        rec_counter += 1
            except Exception:
                pass

    # --- D. Architecture & Coupling (Dependency Graph Metrics) ---
    for node in dep_graph.nodes:
        # High In-Degree Hubs (Depended upon by many files)
        in_degree = sum(1 for e in dep_graph.edges if e.target == node.id)
        if in_degree >= 6:
            ev_id = f"ev_hub_{rec_counter}"
            ev = EvidenceItem(
                id=ev_id,
                type="dependency_graph",
                file=node.relative_path,
                metric="incoming_dependents",
                value=in_degree,
                details=f"`{node.relative_path}` is imported by {in_degree} other project modules."
            )
            all_evidence.append(ev)
            recommendations.append(ImprovementRecommendation(
                id=f"rec_hub_{rec_counter}",
                category="DEPENDENCY_ARCHITECTURE",
                title=f"Protect core dependency hub `{node.label}` ({in_degree} incoming dependents)",
                severity="high",
                confidence=1.0,
                description=f"`{node.relative_path}` is a central architectural component with {in_degree} incoming dependencies.",
                why_it_matters="Changes to high-fan-in modules ripple across the entire codebase and risk breaking dependent modules.",
                recommendation="Ensure this module has 100% regression test coverage and stable public API interfaces.",
                affected_files=[node.relative_path],
                evidence=[ev],
                source="dependency_graph",
                action="Lock interface signatures with type annotations and comprehensive unit tests.",
                is_verified=True
            ))
            rec_counter += 1

    # --- E. Test Coverage Gaps (Coverage.py Metrics if Available) ---
    if coverage_cache:
        file_coverages = coverage_cache.get("files", [])
        for fc in file_coverages:
            file_name = fc.get("file", "")
            cov_pct = fc.get("coverage_percentage", 100.0)
            missing = fc.get("missing_lines", [])
            stmts = fc.get("statements", 0)
            
            if cov_pct < 70 and stmts > 10:
                ev_id = f"ev_cov_{rec_counter}"
                ev = EvidenceItem(
                    id=ev_id,
                    type="coverage",
                    file=file_name,
                    metric="statement_coverage",
                    value=cov_pct,
                    details=f"{cov_pct}% statement coverage ({stmts} executable statements; missing lines: {', '.join(map(str, missing[:8]))}{'...' if len(missing) > 8 else ''})"
                )
                all_evidence.append(ev)
                severity = "high" if cov_pct < 40 else "medium"
                recommendations.append(ImprovementRecommendation(
                    id=f"rec_cov_{rec_counter}",
                    category="TEST_COVERAGE",
                    title=f"Improve test coverage for `{file_name}` ({cov_pct}% covered)",
                    severity=severity,
                    confidence=1.0,
                    description=f"`{file_name}` has {cov_pct}% test coverage with {len(missing)} uncovered statements.",
                    why_it_matters="Uncovered execution paths harbor undetected runtime regressions and edge-case exceptions.",
                    recommendation=f"Add automated test cases targeting uncovered lines: {', '.join(map(str, missing[:10]))}.",
                    affected_files=[file_name],
                    evidence=[ev],
                    source="coverage",
                    action=f"Generate targeted unit tests for `{file_name}`.",
                    is_verified=True
                ))
                rec_counter += 1

    # If no automated tests exist at all for a project with multiple modules:
    if not test_cache and total_loc > 50 and total_files > 0:
        ev_id = f"ev_no_tests_{rec_counter}"
        ev = EvidenceItem(
            id=ev_id,
            type="test",
            file=ast_analysis.files_analyzed[0].relative_path if ast_analysis.files_analyzed else "project",
            metric="test_suite_status",
            value="not_executed",
            details=f"No automated test execution results recorded for {total_files} files."
        )
        all_evidence.append(ev)
        recommendations.append(ImprovementRecommendation(
            id=f"rec_no_tests_{rec_counter}",
            category="TESTING_GAPS",
            title="Establish automated unit test suite baseline",
            severity="medium",
            confidence=1.0,
            description="The codebase does not yet have executed automated unit test results.",
            why_it_matters="Without an automated test suite, refactoring and modernized deployments risk undetected behavioral regressions.",
            recommendation="Use the 'Generated Tests' tab to generate and execute pytest test suites for core modules.",
            affected_files=[f.relative_path for f in ast_analysis.files_analyzed[:5]],
            evidence=[ev],
            source="tests",
            action="Run '3. Generated Tests' to establish automated verification.",
            is_verified=True
        ))
        rec_counter += 1

    # --- 4. Deterministic Severity Sorting & Health Scoring ---
    severity_order = {"high": 3, "medium": 2, "low": 1, "info": 0}
    recommendations.sort(key=lambda r: (severity_order.get(r.severity, 0), r.confidence), reverse=True)

    # Health Scoring Formula:
    # Code Quality: Deduct for syntax errors (20pts) and code smells/large functions (4pts each)
    quality_penalty = (len(syntax_error_files) * 20) + (len(recommendations) * 3)
    code_quality_score = max(35, min(100, 100 - quality_penalty))

    # Architecture Score: Deduct for high coupling bottlenecks
    high_coupling_count = sum(1 for r in recommendations if r.category == "DEPENDENCY_ARCHITECTURE")
    arch_penalty = high_coupling_count * 8
    arch_score = max(40, min(100, 100 - arch_penalty))

    # Test Health: If measured, use actual coverage. Otherwise None.
    test_score = None
    if coverage_cache and coverage_cache.get("coverage_percentage") is not None:
        test_score = int(coverage_cache.get("coverage_percentage"))
    elif test_cache and test_cache.get("passed", 0) > 0:
        pass_ratio = test_cache.get("passed", 0) / max(1, test_cache.get("total", 1))
        test_score = int(pass_ratio * 100)

    # Maintainability score
    maintainability_score = int((code_quality_score + arch_score) / 2)

    # Overall Health
    if test_score is not None:
        overall_score = int((code_quality_score * 0.4) + (arch_score * 0.3) + (test_score * 0.3))
    else:
        overall_score = int((code_quality_score * 0.6) + (arch_score * 0.4))

    health_summary = (
        f"Project health calculated from {total_files} files ({total_loc:,} LOC) across "
        f"AST static analysis and dependency structure."
    )

    health_metrics = ProjectHealthMetrics(
        overall_health_pct=overall_score,
        code_quality_pct=code_quality_score,
        test_health_pct=test_score,
        architecture_pct=arch_score,
        maintainability_pct=maintainability_score,
        health_summary=health_summary
    )

    categories_present = sorted(list({r.category for r in recommendations}))

    return ProjectImprovementsResponse(
        project_id=project_id,
        health_metrics=health_metrics,
        already_done_well=accomplishments,
        recommendations=recommendations,
        total_recommendations=len(recommendations),
        categories_present=categories_present,
        evidence_count=len(all_evidence),
        is_ai_enhanced=False,
        ai_summary=None,
        created_at=time.strftime("%Y-%m-%d %H:%M:%S")
    )


async def explain_improvements_with_ai(
    project_id: str,
    focus_category: Optional[str] = None
) -> ProjectImprovementsResponse:
    """
    On-Demand Layer 2: Groq AI Prioritization & Action Explainer.
    Takes ONLY structured evidence from Layer 1, strictly forbidding hallucination.
    """
    # 1. Always compute deterministic facts first
    base_response = compute_deterministic_improvements(project_id)
    if base_response.total_recommendations == 0:
        base_response.ai_summary = "No significant code smell or coverage issues detected in local analysis."
        return base_response

    # 2. Check if AI Provider is available
    provider = get_ai_provider()
    if not provider or not provider.is_configured:
        base_response.ai_summary = "AI explanation is currently in fallback mode. Deterministic analysis remains fully active."
        return base_response

    # 3. Compact structured evidence prompt
    structured_facts = []
    for r in base_response.recommendations[:10]:
        ev_summaries = [f"ID:{e.id}|{e.metric}={e.value}|file:{e.file}" for e in r.evidence]
        structured_facts.append({
            "title": r.title,
            "category": r.category,
            "severity": r.severity,
            "files": r.affected_files,
            "evidence": ev_summaries
        })

    facts_json = json.dumps(structured_facts, indent=2)

    prompt = (
        f"PROJECT METRICS:\n"
        f"- Files: {len(base_response.already_done_well)}\n"
        f"- Overall Health Score: {base_response.health_metrics.overall_health_pct}%\n"
        f"- Code Quality: {base_response.health_metrics.code_quality_pct}%\n"
        f"- Architecture: {base_response.health_metrics.architecture_pct}%\n\n"
        f"VERIFIED EVIDENCE:\n{facts_json}\n\n"
        f"TASK:\n"
        f"Using ONLY the verified facts above, generate a concise technical improvement roadmap.\n"
        f"STRICT RULES:\n"
        f"- Do NOT invent files or metrics not in the facts.\n"
        f"- Do NOT claim security vulnerabilities or performance bugs without evidence.\n"
        f"- Reference verified evidence items accurately.\n"
        f"- Provide concrete, actionable refactoring steps."
    )

    system_prompt = (
        "You are the CodeOracle Technical Architecture Advisor. You provide strictly evidence-based "
        "software engineering recommendations. Never hallucinate facts or make claims without evidence."
    )

    try:
        ai_res: AIImprovementResponseModel = await provider.generate_structured(
            prompt=prompt,
            schema_class=AIImprovementResponseModel,
            system_prompt=system_prompt,
            max_tokens=600
        )
        base_response.is_ai_enhanced = True
        base_response.ai_summary = ai_res.summary

        # Merge AI explanations into recommendations if matching evidence IDs exist
        ai_map = {rec.title.lower(): rec for rec in ai_res.recommendations}
        for rec in base_response.recommendations:
            for ai_title, ai_rec in ai_map.items():
                if any(w in rec.title.lower() for w in ai_title.split()[:3]):
                    rec.why_it_matters = ai_rec.why_it_matters or rec.why_it_matters
                    rec.action = ai_rec.suggested_action or rec.action
                    break

        return base_response

    except Exception as exc:
        print(f"[AI Improvements Notice]: Groq explanation unavailable: {exc}. Returning verified local data.")
        base_response.ai_summary = "AI reasoning service is currently unavailable. All verified deterministic recommendations are shown below."
        return base_response
