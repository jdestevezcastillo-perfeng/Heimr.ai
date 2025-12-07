import time
import requests
import csv
import random
import threading
import sys
import os

# Configuration
# Detect Minikube IP? Assuming fixed for now based on exploration.
MINIKUBE_IP = "192.168.49.2"
API_PORT = 30809
BASE_URL = f"http://{MINIKUBE_IP}:{API_PORT}"
DEFAULT_DURATION = 600
OUTPUT_FILE = "demo_results.jtl"
CONCURRENCY = 8

def run_user(user_id, start_time, stop_event, writer, lock, duration):
    session = requests.Session()
    while not stop_event.is_set():
        if time.time() - start_time > duration:
            break
            
        endpoint = random.choice(['/api/users', '/api/products', '/api/orders'])
        method = 'POST' if endpoint == '/api/orders' else 'GET'
        
        req_start = time.time()
        error_msg = ""
        success = "true"
        code = 200
        
        try:
            if method == 'GET':
                resp = session.get(f"{BASE_URL}{endpoint}", timeout=10)
            else:
                resp = session.post(f"{BASE_URL}{endpoint}", json={"userId": 1}, timeout=10)
            
            elapsed_ms = int((time.time() - req_start) * 1000)
            code = resp.status_code
            if code >= 400:
                success = "false"
                error_msg = resp.reason
        except Exception as e:
            elapsed_ms = int((time.time() - req_start) * 1000)
            success = "false"
            code = 500
            error_msg = str(e)

        timestamp = int(req_start * 1000)
        
        with lock:
            writer.writerow([
                timestamp, elapsed_ms, endpoint, code, "OK", f"User-{user_id}", "text", success, error_msg, 0, 0, CONCURRENCY, CONCURRENCY, endpoint, elapsed_ms, 0, 0
            ])
        
        time.sleep(random.uniform(0.5, 1.5))

def run_chaos(start_time, stop_event):
    print(f"[{time.time()-start_time:.0f}s] Chaos Generator Started")
    
    # Wait for warm up
    time.sleep(30)
    
    # Phase 2: Error Spikes (30s - 60s)
    print(f"[{time.time()-start_time:.0f}s] >>> INJECTING CHAOS: Error Spikes on /api/error")
    # Hit error endpoint every 0.5s for 30s
    end_phase_2 = time.time() + 30
    while time.time() < end_phase_2 and not stop_event.is_set():
        try:
            requests.get(f"{BASE_URL}/api/error", timeout=2)
        except: pass
        time.sleep(0.5)

    print(f"[{time.time()-start_time:.0f}s] >>> Chaos Phase 1 Complete")
    
    # Phase 3: Cooldown
    time.sleep(10)
        
    # Phase 4: Latency/Blocking (70s - 100s)
    print(f"[{time.time()-start_time:.0f}s] >>> INJECTING CHAOS: Latency/Blocking on /api/slow")
    # Hit slow endpoint (blocks single threaded server)
    end_phase_4 = time.time() + 30
    while time.time() < end_phase_4 and not stop_event.is_set():
        try:
            # Short timeout here because we WANT to trigger parallel requests to block
            requests.get(f"{BASE_URL}/api/slow", timeout=0.1) 
        except: pass
        time.sleep(2) # Don't completely kill it, just intermittent blocking
    
    print(f"[{time.time()-start_time:.0f}s] >>> Chaos Phases Complete")

def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DURATION
    
    print(f"Starting End-to-End Demo Scenario")
    print(f"Target: {BASE_URL}")
    print(f"Duration: {duration} seconds")
    print(f"Output: {OUTPUT_FILE}")
    
    # Check connectivity first
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except Exception as e:
        print(f"Error: Cannot reach {BASE_URL}. Ensure Minikube is running and NodePort service is active.")
        print(f"Details: {e}")
        return

    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timeStamp","elapsed","label","responseCode","responseMessage","threadName","dataType","success","failureMessage","bytes","sentBytes","grpThreads","allThreads","URL","Latency","IdleTime","Connect"])
        
        stop_event = threading.Event()
        lock = threading.Lock()
        threads = []
        start_time = time.time()
        
        for i in range(CONCURRENCY):
            t = threading.Thread(target=run_user, args=(i, start_time, stop_event, writer, lock, duration))
            t.start()
            threads.append(t)
            
        chaos_t = threading.Thread(target=run_chaos, args=(start_time, stop_event))
        chaos_t.start()
        threads.append(chaos_t)

        try:
            while time.time() - start_time < duration:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping early...")
        finally:
            stop_event.set()
            for t in threads:
                t.join()
                
    print(f"Test Complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
