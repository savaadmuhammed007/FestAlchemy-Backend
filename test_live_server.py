import urllib.request
import urllib.parse
import json

BASE_URL = 'http://127.0.0.1:8000'

endpoints = [
    '/db-check/',
    '/api/public/stats/',
    '/api/v1/fest-settings/',
    '/api/v1/categories/',
    '/api/v1/programs/',
    '/api/v1/teams/',
    '/api/v1/stages/',
    '/api/v1/poster-template/',
]

print("--- Testing GET Endpoints on http://127.0.0.1:8000 ---")
for ep in endpoints:
    url = BASE_URL + ep
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            print(f"GET {ep} -> {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"GET {ep} -> HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:300]}")
    except Exception as e:
        print(f"GET {ep} -> FAILED: {e}")

print("\n--- Testing Login API ---")
try:
    data = json.dumps({'username': 'admin', 'password': '123'}).encode('utf-8')
    req = urllib.request.Request(BASE_URL + '/api/auth/login/', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode('utf-8'))
        print("LOGIN RESULT:", res_data)
except urllib.error.HTTPError as e:
    print(f"LOGIN HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}")
except Exception as e:
    print(f"LOGIN FAILED: {e}")
