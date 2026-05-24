import os
import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ---------- TEST S3 ----------
try:
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

    s3.put_object(
        Bucket=os.getenv('S3_BUCKET'),
        Key='test.txt',
        Body=b'hello'
    )

    print("✅ S3 connection works")

except Exception as e:
    print("❌ S3 ERROR")
    print(e)

# ---------- TEST RDS ----------
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

    conn.close()

    print("✅ RDS connection works")

except Exception as e:
    print("❌ RDS ERROR")
    print(e)
