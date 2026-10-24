import os

# main.py and worker.py read these at import time, so set them first.
# The URL is fake: these tests never connect to a database.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["API_KEY"] = "test-key"
