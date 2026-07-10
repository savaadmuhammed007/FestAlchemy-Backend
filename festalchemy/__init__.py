import pymysql

pymysql.version_info = (2, 2, 8, 'final', 0)
pymysql.__version__ = '2.2.8'

# Intercept connection arguments to translate ssl_mode to PyMySQL's ssl parameter
original_connect = pymysql.connect

def custom_connect(*args, **kwargs):
    if 'ssl_mode' in kwargs:
        ssl_mode = kwargs.pop('ssl_mode')
        # If ssl_mode is REQUIRED or PREFERRED, enable SSL for PyMySQL
        if ssl_mode and ssl_mode != 'DISABLED' and 'ssl' not in kwargs:
            kwargs['ssl'] = {}
    return original_connect(*args, **kwargs)

pymysql.connect = custom_connect

pymysql.install_as_MySQLdb()
