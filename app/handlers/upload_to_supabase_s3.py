import os
import boto3
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
    region_name=os.getenv("S3_REGION", "auto"),
)

def upload_file_to_s3(local_path, remote_key):
    bucket = os.getenv("S3_BUCKET")
    with open(local_path, "rb") as f:
        s3.upload_fileobj(f, bucket, remote_key, ExtraArgs={"ContentType": "image/jpeg"})
    return f"{bucket}/{remote_key}"

def download_file_from_s3(remote_key, local_path):
    bucket = os.getenv("S3_BUCKET")
    with open(local_path, "wb") as f:
        s3.download_fileobj(bucket, remote_key, f)
