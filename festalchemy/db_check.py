import traceback
import os
from django.http import JsonResponse
from django.db import connection

def db_check_view(request):
    import hashlib
    db_pass = os.environ.get('DB_PASSWORD', '')
    db_pass_hash = hashlib.sha256(db_pass.encode()).hexdigest()
    expected_hash = '2d298eb9cba849a29552d1043cbe1afef001ecdbd406a996631ba80c9fe8d778'
    diagnostics = {
        "db_password_length": len(db_pass),
        "db_password_starts_with": db_pass[:4] if db_pass else "",
        "db_password_ends_with": db_pass[-4:] if db_pass else "",
        "db_password_matches_expected": db_pass_hash == expected_hash,
        "env_keys": list(os.environ.keys()),
    }
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        return JsonResponse({
            "status": "success",
            "message": "Successfully connected to the database!",
            "result": row,
            "diagnostics": diagnostics
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "diagnostics": diagnostics,
            "traceback": traceback.format_exc()
        }, status=500)
