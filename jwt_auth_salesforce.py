# Retrieve All Logs and Save It to a file in Directory C:\Users\Renan Carriel\Desktop\SOX
# Added Pagination since It retrieves 2000 records at a time


import jwt
import requests
import time
import urllib.parse
import datetime  # Add this import at the top with other imports
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

        # Generate filename with current month and year
        current_date = datetime.datetime.now()
        filename = f"C:\\Users\\Renan Carriel\\Desktop\\SOX\\AuditTrail_{current_date.strftime('%b%y')}.txt"

        # Write results to file
        with open(filename, 'w', encoding='utf-8') as f:
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

        print(f"\nResults have been saved to: {filename}")
            
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