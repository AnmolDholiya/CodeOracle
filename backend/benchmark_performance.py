import io
import os
import time
import zipfile
import string
import random
import tracemalloc
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def generate_realistic_codebase_zip(
    target_mb: float,
    loc_target: int = 1000,
    include_junk: bool = True
) -> bytes:
    """Generates a realistic ZIP archive containing python/js/ts source code,
    as well as realistic node_modules, git, and media files to benchmark realistic extraction.
    """
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Source files (Python, JS, TS)
        files_count = max(5, loc_target // 100)
        lines_per_file = max(10, loc_target // files_count)
        
        for i in range(files_count):
            ext = random.choice([".py", ".js", ".ts", ".jsx", ".tsx"])
            if ext == ".py":
                lines = [
                    f"# Python Module {i}",
                    "import os, sys, json",
                    f"from pkg_{max(0, i-1)}.module_{max(0, i-1)} import HelperClass_{max(0, i-1)}",
                    f"class ServiceHandler_{i}:",
                    f"    def __init__(self, name='service_{i}'):",
                    f"        self.name = name",
                    f"    def process_data_{i}(self, items):",
                    f"        return [item * {i+1} for item in items if item is not None]",
                    "",
                    f"def calculate_metric_{i}(a: int, b: int) -> float:",
                    f"    handler = ServiceHandler_{i}()",
                    f"    return float(a + b * {i+1})",
                ]
            elif ext in (".js", ".jsx"):
                lines = [
                    f"// JavaScript Module {i}",
                    f"import React from 'react';",
                    f"import {{ helper_{max(0, i-1)} }} from './module_{max(0, i-1)}';",
                    f"export const Component_{i} = ({{ title, count }}) => {{",
                    f"    const result = count * {i+1};",
                    f"    return <div className='card_{i}'>{{title}}: {{result}}</div>;",
                    f"}};",
                    f"export function processItem_{i}(val) {{",
                    f"    return val ? val + {i} : null;",
                    f"}}"
                ]
            else: # .ts, .tsx
                lines = [
                    f"// TypeScript Module {i}",
                    f"import {{ Service_{max(0, i-1)} }} from './service_{max(0, i-1)}';",
                    f"export interface Config_{i} {{",
                    f"    id: string;",
                    f"    threshold: number;",
                    f"}}",
                    f"export class Manager_{i} {{",
                    f"    private config: Config_{i};",
                    f"    constructor(cfg: Config_{i}) {{ this.config = cfg; }}",
                    f"    public execute(val: number): number {{ return val * {i+1}; }}",
                    f"}}"
                ]
            
            # Fill remaining lines to reach target LOC
            while len(lines) < lines_per_file:
                lines.append(f"    # Line {len(lines)}: filler computation")
                lines.append(f"    x_{len(lines)} = {len(lines)} * 2")
            
            code_text = "\n".join(lines)
            folder = f"src/pkg_{i // 10}"
            z.writestr(f"{folder}/module_{i}{ext}", code_text)
            
        # 2. Config and doc files
        z.writestr("package.json", '{"name": "benchmark-project", "version": "1.0.0", "dependencies": {"react": "^18.0.0", "axios": "^1.0.0"}}')
        z.writestr("tsconfig.json", '{"compilerOptions": {"target": "es2020", "module": "commonjs"}}')
        z.writestr("README.md", "# Benchmark Codebase\nLegacy codebase stress testing archive.\n")
        
        # 3. Add realistic junk/node_modules/binaries if target_mb > 1 and include_junk is True
        current_size = buf.tell()
        target_bytes = int(target_mb * 1024 * 1024)
        
        if include_junk and target_bytes > current_size:
            # Add node_modules mock files
            for n in range(min(100, int(target_mb * 5))):
                dummy_lib = f"node_modules/mock_pkg_{n}/index.js"
                z.writestr(dummy_lib, f"module.exports = function() {{ return {n}; }};\n")
            
            # Add binary/image mock files
            for img in range(min(30, int(target_mb * 2))):
                dummy_img = f"assets/images/image_{img}.png"
                z.writestr(dummy_img, b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096)
            
            # Fill remaining space with 2-5MB asset chunks (realistic video/bundle/data assets)
            remaining = target_bytes - buf.tell()
            chunk_index = 0
            while remaining > 0:
                asset_size = min(remaining, 5 * 1024 * 1024)
                random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=min(20000, asset_size))).encode('utf-8')
                multiplier = (asset_size // len(random_chars)) + 1
                full_junk = (random_chars * multiplier)[:asset_size]
                z.writestr(f"assets/data/bundle_{chunk_index}.bin", full_junk)
                remaining -= asset_size
                chunk_index += 1
                
    return buf.getvalue()

def run_benchmark(label: str, target_mb: float, loc_target: int):
    print(f"\n========================================================")
    print(f"BENCHMARK: {label} ({target_mb:.1f} MB, ~{loc_target:,} LOC)")
    print(f"========================================================")
    
    t0 = time.time()
    zip_bytes = generate_realistic_codebase_zip(target_mb=target_mb, loc_target=loc_target)
    actual_mb = len(zip_bytes) / (1024 * 1024)
    print(f"[PREPARE] Generated {actual_mb:.2f} MB ZIP in {time.time() - t0:.2f}s")
    
    tracemalloc.start()
    
    # 1. Upload
    t_up_start = time.time()
    res = client.post(
        "/api/projects/upload",
        files={"file": (f"bench_{label.lower().replace(' ', '_')}.zip", zip_bytes, "application/zip")}
    )
    t_upload = time.time() - t_up_start
    assert res.status_code == 202, f"Upload error: {res.text}"
    project_id = res.json()["project_id"]
    print(f"[1. UPLOAD] Streamed upload HTTP 202 in {t_upload:.3f}s (project_id={project_id})")
    
    # 2. Track background stages
    t_bg_start = time.time()
    completed = False
    stage_durations = {}
    stage_start_time = t_bg_start
    current_stage = "queued"
    
    max_wait = 180
    while time.time() - t_bg_start < max_wait:
        st_res = client.get(f"/api/projects/{project_id}/status")
        assert st_res.status_code == 200
        st = st_res.json()
        new_stage = st["stage"]
        
        if new_stage != current_stage:
            now = time.time()
            stage_durations[current_stage] = now - stage_start_time
            print(f"  -> Stage Transition: {current_stage} -> {new_stage} ({st['progress']}%) [{st['message']}]")
            current_stage = new_stage
            stage_start_time = now
            
        if st["status"] == "completed":
            completed = True
            now = time.time()
            stage_durations[current_stage] = now - stage_start_time
            break
        elif st["status"] == "failed":
            raise RuntimeError(f"Processing failed: {st.get('error') or st.get('message')}")
            
        time.sleep(0.05)
        
    t_total_bg = time.time() - t_bg_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert completed, f"Benchmark did not complete within {max_wait}s!"
    
    # Fetch final details
    meta_res = client.get(f"/api/projects/{project_id}")
    meta = meta_res.json()
    
    ast_res = client.get(f"/api/projects/{project_id}/analyze")
    ast_data = ast_res.json()
    
    dep_res = client.get(f"/api/projects/{project_id}/dependencies")
    dep_data = dep_res.json()
    
    client.delete(f"/api/projects/{project_id}")
    
    print(f"\n--- TIMING SUMMARY for {label} ---")
    print(f"Upload Duration:         {t_upload:.3f} s")
    print(f"Total Processing Time:   {t_total_bg:.3f} s")
    print(f"Total Combined Duration: {t_upload + t_total_bg:.3f} s")
    print(f"Files Indexed:           {meta['total_files']} files")
    print(f"Lines of Code Analyzed:  {meta['total_lines_of_code']:,} LOC")
    print(f"AST Symbols Extracted:   {ast_data['total_classes']} classes, {ast_data['total_functions']} functions, {ast_data['total_imports']} imports")
    print(f"Dependency Nodes/Edges:  {len(dep_data['nodes'])} nodes, {len(dep_data['edges'])} edges")
    print(f"Peak Memory Traced:      {peak_mem / (1024 * 1024):.2f} MB")
    
    return {
        "label": label,
        "size_mb": actual_mb,
        "loc": meta['total_lines_of_code'],
        "upload_time": t_upload,
        "bg_processing_time": t_total_bg,
        "total_time": t_upload + t_total_bg,
        "files": meta['total_files'],
        "peak_mem_mb": peak_mem / (1024 * 1024)
    }

if __name__ == "__main__":
    results = []
    # 1 MB
    results.append(run_benchmark("1 MB Codebase", 1.0, loc_target=2000))
    # 10 MB
    results.append(run_benchmark("10 MB Codebase", 10.0, loc_target=15000))
    # 50 MB
    results.append(run_benchmark("50 MB Codebase", 50.0, loc_target=80000))
    # 130 MB with 350,000 LOC target
    results.append(run_benchmark("130 MB Legacy Codebase (350k LOC)", 130.0, loc_target=350000))
    
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETED SUCCESSFULLY FOR ALL SIZES")
    print("=" * 60)
    for r in results:
        print(f"{r['label']:<35} | Size: {r['size_mb']:>6.1f} MB | LOC: {r['loc']:>8,} | Upload: {r['upload_time']:>6.2f}s | Process: {r['bg_processing_time']:>6.2f}s | Total: {r['total_time']:>6.2f}s")
