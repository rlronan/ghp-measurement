try:
    import time
except ImportError as e:
    print(f"Error importing module: {e}")
    for k in range(1000000):
        pass    
try:
    import sys
except ImportError as e:
    print(f"Error importing module: {e}")
    for k in range(1000000):
        pass    
try:
    import requests
    import os
    from escpos.printer import Network
except ImportError as e:
    print(f"Error importing module: {e}")
    time.sleep(60)    
    exit(1)

try:
    unprinted_receipt_spool = []

    domain = "potteryapp.greenwichhouse.org"
    barrow_print_server_secret_key = os.environ.get('BARROW_PRINT_SERVER_SECRET_KEY', '')
    if barrow_print_server_secret_key == '':
        print("Trying to read the BARROW_PRINT_SERVER_SECRET_KEY environment variable failed.")
        print("Will try to read from a file : ./barrow_print_server_secret_key.txt")
        if os.path.exists('./barrow_print_server_secret_key.txt'):
            with open('./barrow_print_server_secret_key.txt', 'r') as f:
                barrow_print_server_secret_key = f.read().strip()
        else:
            print("Could not find the barrow_print_server_secret_key.txt file in the local directory.")
        print("Please set the BARROW_PRINT_SERVER_SECRET_KEY environment variable")
        #exit(1)
except Exception as e:
    print(f"Error setting up print server: {e}")
    time.sleep(60)
    exit(1)

try:
    def fetch_print_jobs():
        try:
            print("Trying to fetch print jobs")
            params = {'secret_key': barrow_print_server_secret_key}
            response = requests.get('https://{}/api/printjobs/'.format(domain), params=params)
            print("Response: ", response)
            #response.raise_for_status()  # Raises an error for bad responses
            print_jobs = response.json()  # Assuming the response is JSON
            print("fetched print jobs: ", print_jobs)
            return print_jobs
        except requests.RequestException as e:
            print(f"Error fetching print jobs: {e}")
            return None
except Exception as e:
    print(f"Error defining fetch_print_jobs: {e}")
    time.sleep(60)
    sys.exit(1)

try:
    def print_to_receipt_printer(jobs):
        # This IP should be the static IP of your receipt printer
        print("Trying to print jobs: ", jobs)
        printed_jobs = []
        PRINTER_IP = '192.168.105.50' 
        print("trying to iterate through print jobs")
        for job in jobs:
            print_text = job['print_string']
            try:
                # Initialize the printer
                try:
                    printer = Network(PRINTER_IP)
                except Exception as e:
                    print(f"Error initializing printer: {e}")
                assert printer.is_usable()

                printer.set(align='center',
                            double_height=True,
                            double_width=True,
                            )
            #    printer.set(normal_textsize=True)
                printer.text(print_text)
                printer.cut()
                printer.close()
                printed_jobs.append(job['id'])
            except Exception as e:
                print(e)
                print("Printer not found on wifi network or not working")
                print(f"Error printing job: {job['id']}")

        return printed_jobs
except Exception as e:
    print(f"Error defining print_to_receipt_printer: {e}")
    time.sleep(60)
    sys.exit(1)


try:
    while True:
        print("\n=========================")
        print(time.ctime())
        if len(unprinted_receipt_spool) > 0:
            print("Unprinted receipt spool: ", unprinted_receipt_spool)
            print("Trying to print unprinted prior jobs")
            try:
                print_success_ids = print_to_receipt_printer(unprinted_receipt_spool)
                print("successfull print ids: ", print_success_ids)
            except Exception as e:
                print(f"Error printing jobs: {e}")
                print_success_ids = []
            unprinted_receipt_spool = [job for job in unprinted_receipt_spool if job['id'] not in print_success_ids]
        
        print_jobs = fetch_print_jobs()
        if print_jobs is None:
            print("No print jobs found")
            time.sleep(60)
            continue
        print_jobs = print_jobs.get('unprinted_receipts', None)
        if print_jobs:
            try: 
                print_success_ids = print_to_receipt_printer(print_jobs)
                print("successfull print ids: ", print_success_ids)
            except Exception as e:
                print(f"Error printing jobs: {e}")
                print_success_ids = []
            for job in print_jobs:
                if job['id'] not in print_success_ids:
                    unprinted_receipt_spool.append(job)
        else:
            print("No print jobs found")
        time.sleep(60)  # Check every 60 seconds
except Exception as e:
    print(f"Error in main loop: {e}")
    time.sleep(60)
    sys.exit(1)