
import requests
from config import SUPABASE_URL, SUPABASE_KEY

def clear_cache():
    print("Clearing API cache from Supabase...")
    
    url = f"{SUPABASE_URL}/rest/v1/api_cache"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "count=exact"
    }
    
    # Supabase requires a filter for DELETE operations to prevent accidental full table wipes.
    # We'll use a condition that matches everything, e.g., hash is not null.
    params = {
        "hash": "neq.NULL"
    }
    
    try:
        response = requests.delete(url, params=params, headers=headers)
        
        if response.status_code in [200, 204]:
            print("Successfully cleared cache.")
            # If count is returned (due to Prefer: count=exact)
            if response.content:
                 # Check if response is JSON (it might be empty for 204)
                try:
                    # Depending on Supabase version, DELETE with count might return the deleted rows or just count info in header
                    # The Content-Range header usually contains the count info like "0-5/6"
                    content_range = response.headers.get('Content-Range')
                    if content_range:
                        print(f"Deleted rows info: {content_range}")
                    else:
                        print("Cache cleared.")
                except:
                    pass
        else:
            print(f"Failed to clear cache. Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clear_cache()
