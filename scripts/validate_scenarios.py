import os
import subprocess
import sys

MOCKS_DIR = "data/mocks"
HEIMR_CMD = [sys.executable, "-m", "heimr.cli", "analyze"]

import argparse
from concurrent.futures import ThreadPoolExecutor

def validate_file(args):
    scenario, filename, filepath, scenario_path, llm_config = args
    
    # Print progress
    print(f"[PROCESSING] {scenario}/{filename}")
    
    # Construct output filename
    report_path = filepath + "_report.md"
    cmd = HEIMR_CMD + [filepath, "--output", report_path, "--explain"]
    
    # Add observability files if they exist
    prom_file = os.path.join(scenario_path, "prometheus_metrics.json")
    if os.path.exists(prom_file):
        cmd.extend(["--prometheus-file", prom_file])
        
    loki_file = os.path.join(scenario_path, "loki_logs.json")
    if os.path.exists(loki_file):
        cmd.extend(["--loki-file", loki_file])
        
    tempo_file = os.path.join(scenario_path, "tempo_traces.json")
    if os.path.exists(tempo_file):
        cmd.extend(["--tempo-file", tempo_file])

    # Add LLM configuration
    if llm_config.get('llm_url'):
        cmd.extend(["--llm-url", llm_config['llm_url']])
    if llm_config.get('llm_model'):
        cmd.extend(["--llm-model", llm_config['llm_model']])
    
    # Set environment variables for API keys
    env = os.environ.copy()
    if llm_config.get('api_key'):
        if llm_config.get('provider') == 'openai':
            env['OPENAI_API_KEY'] = llm_config['api_key']
        elif llm_config.get('provider') == 'anthropic':
            env['ANTHROPIC_API_KEY'] = llm_config['api_key']
    
    try:
        # Run heimr analyze
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print(f"[✓ PASS] {scenario}/{filename}")
            return (True, f"[PASS] {scenario}/{filename}")
        else:
            print(f"[✗ FAIL] {scenario}/{filename}")
            print(f"  Error: {result.stderr.strip()[:200]}")
            return (False, f"[FAIL] {scenario}/{filename}\n  Error: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"[✗ FAIL] {scenario}/{filename} - Exception: {e}")
        return (False, f"[FAIL] {scenario}/{filename} - Exception: {e}")

def run_validation():
    parser = argparse.ArgumentParser(description="Validate Heimr scenarios.")
    parser.add_argument("--llm-url", help="URL for local LLM (e.g., http://localhost:11434/v1)")
    parser.add_argument("--llm-model", help="Model name (e.g., gpt-4, llama3)")
    parser.add_argument("--api-key", help="API Key for OpenAI or Anthropic")
    parser.add_argument("--provider", choices=['openai', 'anthropic', 'local'], help="Provider type (for API key configuration)")
    args = parser.parse_args()

    llm_config = {
        'provider': args.provider,
        'llm_url': args.llm_url,
        'llm_model': args.llm_model,
        'api_key': args.api_key
    }

    if not os.path.exists(MOCKS_DIR):
        print(f"Error: {MOCKS_DIR} not found.")
        return

    scenarios = sorted(os.listdir(MOCKS_DIR))
    tasks = []
    
    print(f"Scanning {len(scenarios)} scenarios...")
    if args.llm_url:
        print(f"Using LLM: Local ({args.llm_model or 'llama3'}) at {args.llm_url}")
    elif args.api_key and args.provider:
        print(f"Using LLM: {args.provider.upper()}")
    else:
        print("Using LLM: Auto-detect from environment variables")
    
    for scenario in scenarios:
        scenario_path = os.path.join(MOCKS_DIR, scenario)
        if not os.path.isdir(scenario_path):
            continue
            
        files = [f for f in os.listdir(scenario_path) if f.endswith(('.csv', '.json', '.log')) 
                 and 'loki' not in f 
                 and 'tempo' not in f 
                 and 'prometheus' not in f]
        
        for filename in files:
            filepath = os.path.join(scenario_path, filename)
            tasks.append((scenario, filename, filepath, scenario_path, llm_config))

    total_files = len(tasks)
    print(f"Found {total_files} files to validate. Starting parallel execution...")
    
    # Use ThreadPoolExecutor to run subprocesses in parallel
    # Adjust max_workers based on CPU/Memory. 
    # Since these are IO/Subprocess bound, we can go higher, but let's be safe with 4-8.
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(validate_file, tasks))
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r[0])
    failed = sum(1 for r in results if not r[0])
    
    print(f"Total: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed scenarios:")
        for success, msg in results:
            if not success:
                print(f"  {msg}")
    
    print("="*60)
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_validation()
