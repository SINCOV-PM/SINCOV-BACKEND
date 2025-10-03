from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
print("URL:", url)

engine = create_engine(url)

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("DB OK:", result.scalar())
except Exception as e:
    print("Error:", e)
