import os
from festalchemy.wsgi import application as app

if __name__ == '__main__':
    port = os.environ.get('PORT', '8000')
    from django.core.management import execute_from_command_line
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
    execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])
