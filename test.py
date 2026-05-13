import os
from dotenv import load_dotenv

load_dotenv()

res = os.getenv("D365FO_CLIENT_ID")
print(res)