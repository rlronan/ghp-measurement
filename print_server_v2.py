# Optimized Print Server Example
# This shows how to update your existing print servers for better efficiency

import time
import sys
import requests
import os
from escpos.printer import Network

# Configuration
LOCATION = "Barrow"  # Change this for each location
DOMAIN = "potteryapp.greenwichhouse.org"
POLL_INTERVAL = 60  # 60 seconds
PRINTER_IP = '192.168.115.147'  # Barrow printer IP

# Load secret key
secret_key = os.environ.get(f'{LOCATION.upper()}_PRINT_SERVER_SECRET_KEY', '')
if not secret_key:
    print(f"Trying to read secret key from file: ./{LOCATION.lower()}_print_server_secret_key.txt")
    try:
        with open(f'./{LOCATION.lower()}_print_server_secret_key.txt', 'r') as f:
            secret_key = f.read().strip()
    except FileNotFoundError:
        print(f"Could not find secret key file. Please set environment variable.")
        sys.exit(1)

def fetch_print_jobs_optimized():
    """
    Fetch print jobs using the optimized endpoint
    """
    try:
        print(f"Fetching print jobs for {LOCATION}")
        params = {
            'secret_key': secret_key,
            'location': LOCATION  # Optional: can be omitted for backward compatibility
        }
        
        # Use the optimized endpoint
        response = requests.get(
            f'https://{DOMAIN}/api/printjobs_v2/',  # New endpoint
            params=params,
            timeout=30  # Add timeout
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Received {data.get('count', 0)} jobs for {data.get('location', LOCATION)}")
            return data.get('unprinted_receipts', [])
        elif response.status_code == 403:
            print("Authentication failed - check secret key")
            return None
        else:
            print(f"Server error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection failed - server may be down")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching jobs: {e}")
        return None

def print_to_receipt_printer_optimized(jobs):
    """
    Optimized printing with better error handling and reporting
    """
    if not jobs:
        return []
    
    print(f"Attempting to print {len(jobs)} jobs")
    printed_jobs = []
    
    for job in jobs:
        job_id = job.get('id')
        print_text = job.get('print_string', '')
        
        if not print_text:
            print(f"No print text for job {job_id}")
            continue
            
        try:
            # Initialize printer with timeout
            printer = Network(PRINTER_IP, timeout=10)
            
            if not printer.is_usable():
                raise Exception("Printer not usable")
                
            # Print with consistent formatting
            printer.set(
                align='center',
                double_height=True,
                double_width=True,
            )
            printer.text(print_text)
            printer.cut()
            printer.close()
            
            printed_jobs.append(job_id)
            print(f"Successfully printed job {job_id}")
            
        except Exception as e:
            print(f"Failed to print job {job_id}: {e}")
    
    # Report results back to server
    # if printed_jobs:
    #     report_print_success(printed_jobs)
    # if failed_jobs:
    #     report_print_failure(failed_jobs)
    
    return printed_jobs

def report_print_success(job_ids):
    """
    Report successful prints back to server
    """
    try:
        params = {
            'secret_key': secret_key,
            'operation': 'mark_printed',
            'receipt_ids': ','.join(map(str, job_ids))
        }
        
        response = requests.post(
            f'https://{DOMAIN}/api/printjobs_v2/',
            data=params,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Successfully reported {result.get('updated', 0)} printed jobs")
        else:
            print(f"Failed to report success: {response.status_code}")
            
    except Exception as e:
        print(f"Error reporting print success: {e}")

def report_print_failure(job_ids, error_msg="Printer communication failed"):
    """
    Report print failures for retry logic
    """
    try:
        params = {
            'secret_key': secret_key,
            'operation': 'report_failure',
            'receipt_ids': ','.join(map(str, job_ids)),
            'error': error_msg
        }
        
        response = requests.post(
            f'https://{DOMAIN}/api/printjobs_v2/',
            data=params,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"Reported {len(job_ids)} failed jobs")
        else:
            print(f"Failed to report failures: {response.status_code}")
            
    except Exception as e:
        print(f"Error reporting failures: {e}")

def main():
    """
    Main print server loop with improved error handling
    """
    print(f"Starting optimized print server for {LOCATION}")
    print(f"Polling interval: {POLL_INTERVAL} seconds")
    print(f"Printer IP: {PRINTER_IP}")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    unprinted_receipt_spool = []

    while True:
        try:
            print(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
            if len(unprinted_receipt_spool) > 0:
                print("Unprinted receipt spool: ", unprinted_receipt_spool)
                print("Trying to print unprinted prior jobs")
        
            # Fetch jobs
            print_jobs = fetch_print_jobs_optimized()
            
            if print_jobs is None:
                consecutive_failures += 1
                print(f"Failed to fetch jobs (attempt {consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    print("Too many consecutive failures. Increasing wait time.")
                    time.sleep(POLL_INTERVAL * 5)  # Wait longer after failures
                    consecutive_failures = 0  # Reset counter
                else:
                    time.sleep(60)  # Short wait before retry
                continue
            
            # Reset failure counter on success
            consecutive_failures = 0
            if not isinstance(print_jobs, list):
                print_jobs = []
            if not isinstance(unprinted_receipt_spool, list):
                unprinted_receipt_spool = []
            print_jobs = print_jobs + unprinted_receipt_spool
            if print_jobs:
                print(f"Processing {len(print_jobs)} print jobs")
                printed_job_ids = print_to_receipt_printer_optimized(print_jobs)
                print(f"Successfully printed {len(printed_job_ids)} jobs")
                unprinted_receipt_spool = [job for job in print_jobs if job['id'] not in printed_job_ids]
                print(f"Failed to print {len(unprinted_receipt_spool)} jobs")
            else:
                print("No print jobs found")
            
            # Wait for next polling cycle
            print(f"Waiting {POLL_INTERVAL} seconds until next check...")
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nShutting down print server...")
            break
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            consecutive_failures += 1
            time.sleep(60)

if __name__ == "__main__":
    main()
