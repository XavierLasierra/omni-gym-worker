import os

# Must be set before app.config is imported (settings are read at import time).
os.environ["WORKER_API_KEY"] = ""
os.environ["HUB_URL"] = "http://hub.test"
