# This filters By:
# 1.Section in Scope
# 2.If Section "Flow", FIlter By Flows In Scope
# 3.Included Created By Name and Only show Valid Sers (Not Unknown)

import jwt
import requests
import time
import urllib.parse
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

    soql_query = "SELECT Action, CreatedDate, Display, Section, CreatedById, CreatedBy.Name FROM SetupAuditTrail WHERE CreatedDate=LAST_MONTH"
    encoded_query = urllib.parse.quote(soql_query)
    query_url = f"{instance_url}/services/data/{API_VERSION}/query?q={encoded_query}"
    
    print("\nAttempting to query Setup Audit Trail...")
    print(f"Making request to: {query_url}")

    try:
        response = requests.get(query_url, headers=headers)
        print(f"Response status code: {response.status_code}")
        
        response.raise_for_status()
        records = response.json()['records']

        print("\nAudit Trail Results:")
        filtered_sections = [
            "Approval Process", "Connected Apps", "Custom Apps", 
            "Delegated Authentication Configuration", "Flows", 
            "Inbound Change Sets", "Manage Users", 
            "OAuth Client Credentials User", "Password Policies",
            "Remote Access", "SAML Configuration", "Session Settings",
            "Validation Rules"
        ]
        flow_actions = [
            "FF PSA - Copy Percent Complete Costs to RTL", "FF PSA: Milestone Assignments",
            "FF PSA: Set Milestone Recognition Method", "FF PSA: Set Project Recognition Method", 
            "FF PSA: Set Timecard Split Recognition Method", "FF PSA: Update Timecard for Rev Rec - Auto Launched",
            "FF PSA: Update Total Recognized To Date On Project - Scheduled",
            "FFX PSA Actual Date Approves And Closes Milestone", "FFX PSA Approved Budget",
            "FFX PSA Assignment Set Bill Rate from Rate Card For Non-Fixed Price Projects",
            "FFX PSA Billable Project Defaults On Create", "FFX PSA Exclude 0 Billable Amounts on Timecard Splits",
            "FFX PSA Milestone Creation Default", "FFX PSA Misc Adjustment Approved False",
            "FFX PSA Misc Adjustment Approved True", "FFX PSA Project Activation based on Stage",
            "FFX PSA Project Closure Based on Stage", "FFX PSA Set Assignment Cost Rate From Rate Card",
            "FFX PSA Set RR Bill Rate to 0 for Fixed Price Projects - V1"
        ]
        for record in records:
            if record['Section'] in filtered_sections:
                created_by = record['CreatedBy']['Name'] if record['CreatedBy'] else 'Unknown'
                if created_by != 'Unknown':
                    if record['Section'] == "Flows":
                        if record['Action'] in flow_actions:
                            print(f"Time: {record['CreatedDate']}")
                            print(f"Action: {record['Action']}")
                            print(f"Details: {record['Display']}")
                            print(f"Section: {record['Section']}")
                            print(f"Created By: {created_by}")
                            print(f"Created By ID: {record['CreatedById']}")
                            print("-" * 50)
                    else:
                        print(f"Time: {record['CreatedDate']}")
                        print(f"Action: {record['Action']}")
                        print(f"Details: {record['Display']}")
                        print(f"Section: {record['Section']}")
                        print(f"Created By: {created_by}")
                        print(f"Created By ID: {record['CreatedById']}")
                        print("-" * 50)
            
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