import os
import io
import time
import shutil
import tempfile
import zipfile
from app.services.extractor import (
    init_project_workspace,
    cleanup_project,
    MAX_FILE_COUNT,
    MAX_UNCOMPRESSED_SIZE,
    MAX_SINGLE_FILE_SIZE,
    is_safe_path
)
from app.services.file_classifier import should_extract_archive_entry
from app.services.python_ast import scan_and_analyze_workspace
from app.services.dependency_graph import generate_dependency_graph
from benchmark_performance import generate_realistic_codebase_zip

def measure_stage_breakdown(label: str, target_mb: float, loc: int):
    print(f"\n========================================================")
    print(f"MEASURING DETAILED STAGES FOR: {label} ({target_mb:.1f} MB, {loc:,} LOC)")
    print(f"========================================================")
    
    zip_bytes = generate_realistic_codebase_zip(target_mb=target_mb, loc_target=loc)
    actual_mb = len(zip_bytes) / (1024 * 1024)
    
    # 1. Upload / Streaming Write to Disk
    t0 = time.time()
    project_id, project_dir, zip_path = init_project_workspace(f"{label}.zip")
    with open(zip_path, "wb") as f:
        # simulate 1MB chunks
        chunk_size = 1024 * 1024
        for i in range(0, len(zip_bytes), chunk_size):
            f.write(zip_bytes[i:i+chunk_size])
    t_upload = time.time() - t0
    
    # 2. Filtered Extraction
    t0 = time.time()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.infolist()
        to_extract = [m for m in members if should_extract_archive_entry(m.filename)]
        for m in to_extract:
            zip_ref.extract(m, project_dir)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    t_extract = time.time() - t0
    
    # 3. File Scanning & AST Analysis (Unified Parallel)
    t0 = time.time()
    metadata, ast_analysis = scan_and_analyze_workspace(project_dir, project_id, f"{label}.zip")
    t_analysis = time.time() - t0
    
    # 4. Dependency Graph Generation
    t0 = time.time()
    graph = generate_dependency_graph(ast_analysis)
    t_deps = time.time() - t0
    
    t_total = t_upload + t_extract + t_analysis + t_deps
    
    print(f"  • Upload (Streaming Write): {t_upload:.4f} s")
    print(f"  • Filtered Extraction:      {t_extract:.4f} s")
    print(f"  • Scan & AST Analysis:      {t_analysis:.4f} s")
    print(f"  • Dependency Graph:         {t_deps:.4f} s")
    print(f"  • Total Pipeline Duration:  {t_total:.4f} s")
    print(f"  • Files Extracted & Parsed: {metadata.total_files} files, {metadata.total_lines_of_code:,} LOC")
    print(f"  • Symbols Extracted:        {ast_analysis.total_classes} classes, {ast_analysis.total_functions} functions")
    print(f"  • Graph Size:               {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    
    cleanup_project(project_id)
    
    return {
        "label": label,
        "size_mb": actual_mb,
        "loc": metadata.total_lines_of_code,
        "upload": t_upload,
        "extraction": t_extract,
        "analysis": t_analysis,
        "deps": t_deps,
        "total": t_total
    }

if __name__ == "__main__":
    results = []
    results.append(measure_stage_breakdown("1 MB ZIP", 1.0, 2000))
    results.append(measure_stage_breakdown("10 MB ZIP", 10.0, 15000))
    results.append(measure_stage_breakdown("50 MB ZIP", 50.0, 80000))
    results.append(measure_stage_breakdown("130 MB ZIP (350k LOC)", 130.0, 350000))
    
    print("\n" + "=" * 80)
    print(f"{'ARCHIVE':<25} | {'UPLOAD':<10} | {'EXTRACT':<10} | {'ANALYSIS':<10} | {'DEPS':<10} | {'TOTAL':<10}")
    print("=" * 80)
    for r in results:
        print(f"{r['label']:<25} | {r['upload']:>8.3f}s | {r['extraction']:>8.3f}s | {r['analysis']:>8.3f}s | {r['deps']:>8.3f}s | {r['total']:>8.3f}s")
