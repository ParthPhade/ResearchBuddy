import os
import sys
import json
import requests
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configuration
API_URL = "http://localhost:8000"
TOKEN_FILE = "token.json"
# You need to download your client_secrets.json from Google Cloud Console
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

def login():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"Error: {CLIENT_SECRETS_FILE} not found.")
                print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    print("Successfully authenticated!")
    return creds

def summarize(file_path, provider="gemini"):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds:
        print("Please login first using 'python cli.py login'")
        return

    # Use the ID token for backend verification
    headers = {
        "Authorization": f"Bearer {creds.id_token}"
    }

    print(f"Summarizing {file_path} using {provider}...")
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
        params = {'provider': provider}
        try:
            response = requests.post(f"{API_URL}/summarize", headers=headers, files=files, params=params)
            if response.status_code == 200:
                print("\n--- Summary ---\n")
                print(response.json().get('summary'))
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Request failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="ResearchBuddy CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Login command
    subparsers.add_parser("login", help="Login with Google")

    # Summarize command
    sum_parser = subparsers.add_parser("summarize", help="Summarize a research paper")
    sum_parser.add_argument("file", help="Path to the PDF file")
    sum_parser.add_argument("--provider", default="gemini", choices=["gemini", "openai"], help="AI Provider")

    args = parser.parse_args()

    if args.command == "login":
        login()
    elif args.command == "summarize":
        summarize(args.file, args.provider)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
