import os
import sys
import requests
import base64
from dotenv import load_dotenv

# --- Configuration Loaded from Environment ---
load_dotenv()
ORG_URL = os.getenv("ADO_ORG_URL")
PROJECT = os.getenv("ADO_PROJECT")
PAT = os.getenv("ADO_PAT")

def validate_env():
    missing = []
    if not ORG_URL: missing.append("ADO_ORG_URL")
    if not PROJECT: missing.append("ADO_PROJECT")
    if not PAT: missing.append("ADO_PAT")
    
    if missing:
        print("❌ Error: Missing environment variables:")
        for m in missing:
            print(f"   - {m}")
        print("\nUsage example:")
        print("   export ADO_ORG_URL='https://dev.azure.com/MyOrg'")
        print("   export ADO_PROJECT='My Project'")
        print("   export ADO_PAT='...'")
        sys.exit(1)

def get_backlog():
    validate_env()
    
    # Encode PAT
    auth = base64.b64encode(f":{PAT}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    print(f"🔍 Connecting to '{PROJECT}'...")
    
    # 1. WIQL Query
    # Note: We use replace to handle spaces in URL, but keep spaces in the WIQL query string
    safe_proj_url = PROJECT.replace(" ", "%20")
    wiql_url = f"{ORG_URL}/{safe_proj_url}/_apis/wit/wiql?api-version=7.0"
    
    query = {
        "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{PROJECT}' AND [System.State] <> 'Closed' ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
    }
    
    try:
        res = requests.post(wiql_url, headers=headers, json=query)
        if res.status_code != 200:
            print(f"❌ API Error ({res.status_code}): {res.text}")
            return
            
        work_items = res.json().get("workItems", [])
        ids = [str(item["id"]) for item in work_items]
        
        if not ids:
            print("⚠️  No open items found in backlog.")
            return

        print(f"✅ Found {len(ids)} items. Fetching details...")

        # 2. Get Details
        ids_str = ",".join(ids[:200])
        fields = "System.Id,System.Title,Microsoft.VSTS.Common.Priority,System.State"
        details_url = f"{ORG_URL}/{safe_proj_url}/_apis/wit/workitems?ids={ids_str}&fields={fields}&api-version=7.0"
        
        res_details = requests.get(details_url, headers=headers)
        items_data = res_details.json().get("value", [])

        # 3. Display
        print("\n" + "="*85)
        print(f"{'ID':<6} | {'PRIORITY':<8} | {'STATE':<12} | {'TITLE'}")
        print("-"*85)
        
        for item in items_data:
            f = item["fields"]
            print(f"{item['id']:<6} | {f.get('Microsoft.VSTS.Common.Priority', '-'):<8} | {f.get('System.State', '-'):<12} | {f.get('System.Title', '')}")
        print("="*85 + "\n")

    except Exception as e:
        print(f"❌ Critical Error: {str(e)}")

if __name__ == "__main__":
    get_backlog()
