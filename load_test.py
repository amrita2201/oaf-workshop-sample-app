import concurrent.futures
import sys
import time
import requests

# Check if ALB address was provided as an argument
if len(sys.argv) < 2:
    print("Error: Missing ALB address.")
    print("Usage: python3 load_test.py <alb_dns_or_url>")
    print("Example: python3 load_test.py test-alb-2031674237.us-east-1.elb.amazonaws.com")
    sys.exit(1)

# Format the input URL cleanly
alb_input = sys.argv[1].strip()
if not alb_input.startswith("http://") and not alb_input.startswith("https://"):
    ALB_URL = f"http://{alb_input}/"
else:
    ALB_URL = alb_input if alb_input.endswith("/") else f"{alb_input}/"

# Configuring the settings
TOTAL_REQUESTS = 50000     # Total requests to send
CONCURRENT_THREADS = 50   # Number of parallel workers
TIMEOUT = 5               # Request timeout in seconds

def send_request(request_num):
    """Sends a single GET request to the load balancer."""
    try:
        response = requests.get(ALB_URL, timeout=TIMEOUT)
        return response.status_code
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

def run_load_test():
    print(f"Starting load test against {ALB_URL}...")
    print(f"Sending {TOTAL_REQUESTS} requests across {CONCURRENT_THREADS} parallel threads.\n")
    
    start_time = time.time()
    success_count = 0
    error_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        futures = [executor.submit(send_request, i) for i in range(TOTAL_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result == 200:
                success_count += 1
            else:
                error_count += 1

    duration = round(time.time() - start_time, 2)
    rps = round(TOTAL_REQUESTS / duration, 2)

    print("-" * 40)
    print("LOAD TEST COMPLETED")
    print("-" * 40)
    print(f"Total Time Taken:     {duration} seconds")
    print(f"Successful (200 OK):  {success_count}")
    print(f"Failed / Errors:      {error_count}")
    print(f"Requests Per Second:  {rps} req/sec")

if __name__ == "__main__":
    run_load_test()
