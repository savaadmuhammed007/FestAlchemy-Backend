import os

# Render provides the port in the PORT environment variable (default 10000)
port = os.environ.get("PORT", "10000")

# Crucial: Must bind to 0.0.0.0 so Render's internal port scanner detects it
bind = f"0.0.0.0:{port}"

# Performance and stability settings
workers = 2
threads = 4
worker_class = "gthread"
timeout = 120
keepalive = 5

# Ensure all logs go to stdout/stderr so they appear in the Render Dashboard
accesslog = "-"
errorlog = "-"
loglevel = "info"
