import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY",)
MODEL_NAME = os.getenv("MODEL_NAME", )
DATABASE_URL = os.getenv("DATABASE_URL", )
JWT_SECRET = os.getenv("JWT_SECRET", )
SECRET_KEY = os.getenv("SECRET_KEY") or JWT_SECRET
ADMIN_CODE = os.getenv("ADMIN_CODE", )
ALGORITHUM = os.getenv("ALGORITHUM", )
ALGORITHM = os.getenv("ALGORITHM") or ALGORITHUM or "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "30"))
REFUND_APPROVAL_THRESHOLD = 100.0
MAX_REFUND_AMOUNT = os.getenv("MAX_REFUND_AMOUNT",)
REFUND_WINDOW_DAYS = os.getenv("REFUND_WINDOW_DAYS", )
MAX_RETRIES = os.getenv("MAX_RETRIES", )
MAX_REWRITES = os.getenv("MAX_REWRITES", MAX_RETRIES or "2")