import os
import boto3
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

response = s3.list_objects_v2(
    Bucket=os.getenv("S3_BUCKET"),
    Prefix="raw/flights/"
)

files = response.get("Contents", [])

print(f"\nFiles in S3: {len(files)}\n")

for f in files:
    print(f"{f['Key']}  ({f['Size']:,} bytes)")
