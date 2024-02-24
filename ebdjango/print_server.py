import requests
import time
import os
from escpos.printer import Network
domain = "potteryapp.greenwichhouse.org"
print_server_secret_key = os.environ.get('PRINT_SERVER_SECRET_KEY')
def fetch_print_jobs():
    try:
        print("Trying to fetch print jobs")
        params = {'secret_key': print_server_secret_key}
        response = requests.get('http://{}/api/printjobs/'.format(domain), params=params)
        print("Response: ", response)
        response.raise_for_status()  # Raises an error for bad responses
        print_jobs = response.json()  # Assuming the response is JSON
        return print_jobs
    except requests.RequestException as e:
        print(f"Error fetching print jobs: {e}")
        return None

def job_to_printer_text(job):
    # Process the job and return the text to be printed
    if job['receipt_type'] == 'Bisque':
        print_string = """
BISQUE FIRING SLIP - DO NOT THROW AWAY
PLACE THIS SLIP WITH YOUR PIECE ON THE
APPROPRIATE BISQUE FIRING SHELF
Name: {}

Date: {}

LxWxH: {} x {} x {}

Handles: {}  Size: {}

Course Number: {}

Bisque Temp: {}


""".format(job['ghp_user_name'], job['piece_date'], job['length'], job['width'], job['height'], job['handles'], job['size'], job['course_number'], job['glaze_temp'])

    elif job['receipt_type'] == 'Glaze':
        print_string = """
GLAZE FIRING SLIP - DO NOT THROW AWAY
PLACE THIS SLIP WITH YOUR PIECE ON THE
APPROPRIATE GLAZE FIRING SHELF

Name: {}

Date: {}

LxWxH: {} x {} x {}

Handles: {}  Size: {}

Course Number: {}

Glaze Temp: {}


""".format(job['ghp_user_name'], job['piece_date'], job['length'], job['width'], job['height'], job['handles'], job['size'], job['course_number'], job['glaze_temp'])

    return print_string

def print_to_receipt_printer(jobs):
    # This IP should be the static IP of your receipt printer
    printed_jobs = []
    PRINTER_IP = '10.186.3.27'
    for job in print_jobs:
        print_text = job_to_printer_text(job)
        try:
            # Initialize the printer
            printer = Network(PRINTER_IP)
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
            print(f"Error printing job: {job['id']}")

    return printed_jobs

def return_print_job_results(printed_jobs):
    try:
        print("Trying to return print job status")
        params = {'secret_key': print_server_secret_key,
                  'receipt_ids': printed_jobs}
        response = requests.post('http://127.0.0.1:8000/api/printjobs/', params=params)
        print("Response: ", response)
        response.raise_for_status()  # Raises an error for bad responses
        #print_jobs = response.json()  # Assuming the response is JSON
        return response
    except requests.RequestException as e:
        print(f"Error returning print job status: {e}")
        return None



#return_print_job_results(printed_jobs)

while True:
    print_jobs = fetch_print_jobs()
    print_jobs = print_jobs['unprinted_receipts']
    if print_jobs:
        printed_jobs = print_to_receipt_printer(print_jobs)
        print(printed_jobs)
    time.sleep(60)  # Check every 60 seconds