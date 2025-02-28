# Retrieve All Logs and Save It to a file in Directory C:\Users\Renan Carriel\Desktop\SOX
# Added Pagination since It retrieves 2000 records at a time
# Added Filtered Sections
# Added Filtered Results to a new file
# Added Flows Section and Filtered Flows In Scope
# Added Custom Apps Section and Filtered Created By Certinia
# Added Manage Users Section and Filtered Changed Profile to System Administrator, Department Administrator, Admin Revenue Management, and PSA Administrator
# Added .env file to store credentials

import jwt
import requests
import time
import urllib.parse
import datetime
from dotenv import load_dotenv  # Add this import
import os  # Add this import

# Load environment variables
load_dotenv('FullSandbox.env')

# Configuration from environment variables
CLIENT_ID = os.getenv('SF_CLIENT_ID')
USERNAME = os.getenv('SF_USERNAME')
PRIVATE_KEY_FILE = os.getenv('SF_PRIVATE_KEY_FILE')
SALESFORCE_URL = os.getenv('SF_URL')
API_VERSION = os.getenv('SF_API_VERSION')

def generate_jwt():
    with open(PRIVATE_KEY_FILE, "r") as key_file:
        private_key = key_file.read()

    payload = {
        "iss": CLIENT_ID,
        "sub": USERNAME,
        "aud": SALESFORCE_URL,
        "exp": int(time.time()) + 300,  # 5 minutes expiration
    }

    try:
        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
        print("JWT token generated successfully")
        return jwt_token
    except Exception as e:
        print(f"Error generating JWT token: {e}")
        return None

def authenticate_with_salesforce():
    jwt_token = generate_jwt()
    if not jwt_token:
        return None, None

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }

    try:
        response = requests.post(f"{SALESFORCE_URL}/services/oauth2/token", data=data)
        response.raise_for_status()

        response_data = response.json()
        print("Authentication successful!")
        print(f"Instance URL: {response_data['instance_url']}")
        return response_data["access_token"], response_data["instance_url"]
    except requests.exceptions.RequestException as e:
        print("Authentication failed!")
        print(f"Error: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        return None, None

def query_audit_trail(access_token, instance_url):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Define sections to filter
    filtered_sections = {
        "Approval Process", "Connected Apps", "Custom Apps", 
        "Delegated Authentication Configuration", "Flows", 
        "Inbound Change Sets", "Manage Users", 
        "OAuth Client Credentials User", "Password Policies", 
        "Remote Access", "SAML Configuration", "Session Settings", 
        "Validation Rules"
    }

    # Define specific Flow names to filter
    flow_filters = {
        "FF PSA - Copy Percent Complete Costs to RTL",
        "FF PSA: Milestone Assignments",
        "FF PSA: Set Milestone Recognition Method",
        "FF PSA: Set Project Recognition Method",
        "FF PSA: Set Timecard Split Recognition Method",
        "FF PSA: Update Timecard for Rev Rec - Auto Launched",
        "FF PSA: Update Total Recognized To Date On Project - Scheduled",
        "FFX PSA Actual Date Approves And Closes Milestone",
        "FFX PSA Approved Budget",
        "FFX PSA Assignment Set Bill Rate from Rate Card For Non-Fixed Price Projects",
        "FFX PSA Billable Project Defaults On Create",
        "FFX PSA Exclude 0 Billable Amounts on Timecard Splits",
        "FFX PSA Milestone Creation Default",
        "FFX PSA Misc Adjustment Approved False",
        "FFX PSA Misc Adjustment Approved True",
        "FFX PSA Project Activation based on Stage",
        "FFX PSA Project Closure Based on Stage",
        "FFX PSA Set Assignment Cost Rate From Rate Card",
        "FFX PSA Set RR Bill Rate to 0 for Fixed Price Projects - V1"
    }

    soql_query = "SELECT Action, CreatedDate, Display, Section, CreatedById, CreatedBy.Name FROM SetupAuditTrail"
    encoded_query = urllib.parse.quote(soql_query)
    query_url = f"{instance_url}/services/data/{API_VERSION}/query?q={encoded_query}"
    
    print("\nAttempting to query Setup Audit Trail...")
    print(f"Making request to: {query_url}")

    try:
        all_records = []
        
        # Get initial response
        response = requests.get(query_url, headers=headers)
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        all_records.extend(response_data['records'])
        
        # Handle pagination
        while 'nextRecordsUrl' in response_data:
            print("Retrieving next batch of records...")
            next_url = f"{instance_url}{response_data['nextRecordsUrl']}"
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            all_records.extend(response_data['records'])

        print(f"Total records retrieved: {len(all_records)}")

        # Generate filenames with current month and year
        current_date = datetime.datetime.now()
        base_filename = f"AuditTrail_{current_date.strftime('%b%y')}"
        original_filename = f"C:\\Users\\Renan Carriel\\Desktop\\SOX\\{base_filename}.txt"
        filtered_filename = f"C:\\Users\\Renan Carriel\\Desktop\\SOX\\{base_filename}Filtered.txt"

        # Filter records
        filtered_records = []
        for record in all_records:
            if record['Section'] in filtered_sections:
                # Filter for Manage Users section
                if record['Section'] == "Manage Users":
                    details = record['Display']
                    if (("Changed Profile" in details and "System Administrator" in details) or
                        ("Changed Profile" in details and "Department Administrator" in details) or
                        ("Permission set group" in details and "Admin Revenue Management" in details) or
                        ("Permission set group" in details and "PSA Administrator" in details)):
                        filtered_records.append(record)
                # Filter for Flows section
                elif record['Section'] == "Flows":
                    if any(flow_name in record['Display'] for flow_name in flow_filters):
                        filtered_records.append(record)
                # Filter for Custom Apps section
                elif record['Section'] == "Custom Apps":
                    if record['CreatedBy'] and "Certinia" in record['CreatedBy']['Name']:
                        filtered_records.append(record)
                else:
                    filtered_records.append(record)

        # Write original results to file
        with open(original_filename, 'w', encoding='utf-8') as f:
            f.write("Salesforce Audit Trail Report\n")
            f.write(f"Generated on: {current_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Records: {len(all_records)}\n")
            f.write("=" * 50 + "\n\n")
            
            for record in all_records:
                f.write(f"Time: {record['CreatedDate']}\n")
                f.write(f"Action: {record['Action']}\n")
                f.write(f"Details: {record['Display']}\n")
                f.write(f"Section: {record['Section']}\n")
                f.write(f"Created By: {record['CreatedBy']['Name'] if record['CreatedBy'] else 'Automated User'}\n")
                f.write(f"Created By ID: {record['CreatedById']}\n")
                f.write("-" * 50 + "\n")

        # Write filtered results to new file
        with open(filtered_filename, 'w', encoding='utf-8') as f:
            f.write("Salesforce Filtered Audit Trail Report\n")
            f.write(f"Generated on: {current_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Filtered Records: {len(filtered_records)}\n")
            f.write("Filtered Sections: " + ", ".join(filtered_sections) + "\n")
            f.write("=" * 50 + "\n\n")
            
            for record in filtered_records:
                f.write(f"Time: {record['CreatedDate']}\n")
                f.write(f"Action: {record['Action']}\n")
                f.write(f"Details: {record['Display']}\n")
                f.write(f"Section: {record['Section']}\n")
                f.write(f"Created By: {record['CreatedBy']['Name'] if record['CreatedBy'] else 'Automated User'}\n")
                f.write(f"Created By ID: {record['CreatedById']}\n")
                f.write("-" * 50 + "\n")

        print(f"\nOriginal results have been saved to: {original_filename}")
        print(f"Filtered results have been saved to: {filtered_filename}")
        print(f"Total records in filtered file: {len(filtered_records)}")
            
    except requests.exceptions.RequestException as e:
        print(f"Query failed: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    access_token, instance_url = authenticate_with_salesforce()
    if access_token and instance_url:
        query_audit_trail(access_token, instance_url)
    else:
        print("Authentication failed. Cannot proceed with queries.")