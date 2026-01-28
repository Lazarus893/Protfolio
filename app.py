from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import hashlib
import json
from analyze_session import analyze_session, analyze_daily_summary
from config import SUPABASE_URL, SUPABASE_KEY

app = Flask(__name__, static_folder='.')

# Configuration
REMOTE_API_ENDPOINT = "https://api-llm-internal.prd.alva.xyz/query"

def get_from_cache(cache_key):
    try:
        url = f"{SUPABASE_URL}/rest/v1/api_cache"
        params = {
            "hash": f"eq.{cache_key}",
            "select": "response"
        }
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return data[0]['response']
        return None
    except Exception as e:
        print(f"Supabase read error: {e}")
        return None

def save_to_cache(cache_key, response_data):
    try:
        url = f"{SUPABASE_URL}/rest/v1/api_cache"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        payload = {
            "hash": cache_key,
            "response": response_data
        }
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Supabase write error: {e}")

def get_analysis_from_cache(session_id):
    try:
        url = f"{SUPABASE_URL}/rest/v1/session_analysis"
        params = {
            "session_id": f"eq.{session_id}",
            "select": "analysis"
        }
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return data[0]['analysis']
        return None
    except Exception as e:
        print(f"Analysis cache read error: {e}")
        return None

def save_analysis_to_cache(session_id, analysis_data):
    try:
        url = f"{SUPABASE_URL}/rest/v1/session_analysis"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        payload = {
            "session_id": session_id,
            "analysis": analysis_data
        }
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Analysis cache write error: {e}")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/query', methods=['POST'])
def proxy_query():
    try:
        # Forward the headers (especially Authorization)
        excluded_headers = ['content-length', 'host', 'content-type', 'connection', 'accept-encoding']
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in excluded_headers
        }
        
        # Get the JSON body
        data = request.get_json()
        
        # Generate Cache Key (SHA256 of sorted JSON)
        data_str = json.dumps(data, sort_keys=True)
        cache_key = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        
        # Check for force refresh header
        force_refresh = request.headers.get('X-Force-Refresh') == 'true'
        
        # 1. Try to get from Cache
        if not force_refresh:
            cached_data = get_from_cache(cache_key)
            if cached_data:
                print(f"Cache HIT for {cache_key[:8]}")
                return jsonify(cached_data), 200
        else:
            print(f"Force Refresh: Skipping cache for {cache_key[:8]}")

        # 2. If miss, fetch from remote API
        print(f"Cache MISS for {cache_key[:8]}")
        try:
            resp = requests.post(
                REMOTE_API_ENDPOINT,
                json=data,
                headers=headers
            )
        except Exception as e:
            print(f"Remote API Connection Error: {e}")
            return jsonify({"errors": [{"message": "Failed to connect to remote API"}]}), 502
        
        # 3. Process Response
        if resp.status_code != 200:
            print(f"Remote API Error: {resp.status_code} - {resp.text[:200]}")

        response_json = None
        try:
            response_json = resp.json()
        except:
            # If not JSON, return as is (and don't cache non-json)
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            resp_headers = [(name, value) for (name, value) in resp.headers.items() 
                           if name.lower() not in excluded_headers]
            return (resp.content, resp.status_code, resp_headers)

        # 4. Save to Cache (only if successful)
        if resp.status_code == 200:
            save_to_cache(cache_key, response_json)
            print(f"Cache SAVED for {cache_key[:8]}")

        return jsonify(response_json), resp.status_code
        
    except Exception as e:
        return jsonify({"errors": [{"message": str(e)}]}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        session_id = data.get('id')
        
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400

        # 1. Check cache first
        cached_analysis = get_analysis_from_cache(session_id)
        if cached_analysis:
            print(f"Analysis Cache HIT for session {session_id}")
            return jsonify(cached_analysis), 200
            
        print(f"Analysis Cache MISS for session {session_id}")
        
        # 2. Perform analysis
        result = analyze_session(data)
        
        # 3. Save to cache if successful
        if result and "error" not in result:
            save_analysis_to_cache(session_id, result)
            print(f"Analysis Cache SAVED for session {session_id}")
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_day', methods=['POST'])
def analyze_day():
    try:
        data = request.get_json()
        sessions = data.get('sessions', [])
        
        if not sessions:
            return jsonify({"error": "No sessions data provided"}), 400
            
        result = analyze_daily_summary(sessions)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting server at http://localhost:{port}")
    print(f"Proxying requests to {REMOTE_API_ENDPOINT}")
    app.run(host='0.0.0.0', port=port, debug=True)
