import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'db/schema.json')
ANALYTICS_KEY = os.getenv("ANALYTICS_KEY", None)