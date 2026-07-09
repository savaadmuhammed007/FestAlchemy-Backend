import traceback
from django.http import JsonResponse
from django.db import connection

def db_check_view(request):
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        return JsonResponse({
            "status": "success",
            "message": "Successfully connected to the database!",
            "result": row
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }, status=500)
