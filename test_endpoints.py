import os
import sys
import django
import traceback

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

client = Client()

print("--- Testing Unauthenticated Endpoints ---")
urls = [
    '/db-check/',
    '/api/public/stats/',
    '/api/v1/fest-settings/',
    '/api/v1/categories/',
    '/api/v1/programs/',
    '/api/v1/teams/',
    '/api/v1/stages/',
    '/api/v1/poster-template/',
]

for url in urls:
    try:
        response = client.get(url)
        print(f"GET {url} -> {response.status_code}")
        if response.status_code == 500:
            print("ERROR CONTENT:", response.content.decode('utf-8', errors='ignore')[:500])
    except Exception as e:
        print(f"GET {url} -> EXCEPTION: {e}")
        traceback.print_exc()

print("\n--- Testing Authenticated Endpoints (Admin User) ---")
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
if user:
    client.force_login(user)
    auth_urls = [
        '/api/auth/me/',
        '/api/admin/stats/',
        '/api/v1/members/',
        '/api/v1/marksheets/',
        '/api/v1/results/',
        '/api/v1/users/',
        '/api/reports/?type=team_standings',
        '/api/reports/?type=program_results',
        '/api/reports/?type=schedule',
        '/api/reports/?type=registered_participants',
    ]
    for url in auth_urls:
        try:
            response = client.get(url)
            print(f"GET {url} -> {response.status_code}")
            if response.status_code == 500:
                print("ERROR CONTENT:", response.content.decode('utf-8', errors='ignore')[:500])
        except Exception as e:
            print(f"GET {url} -> EXCEPTION: {e}")
            traceback.print_exc()
else:
    print("No user found to test auth endpoints.")
