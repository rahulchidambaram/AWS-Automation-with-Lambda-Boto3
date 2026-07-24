"""
Assignment 1: Automated S3 Bucket Cleanup (Objects Older Than 30 Days)
 
Deletes objects in a given S3 bucket whose LastModified timestamp is older
than a configurable age threshold.
 
FOR TESTING: set AGE_THRESHOLD_MINUTES (e.g. 5) via the Lambda env var
or the fallback below, so you don't have to wait 30 real days to see it work.
FOR FINAL SUBMISSION: switch back to the 30-day threshold.
"""


import boto3
from datetime import datetime, timezone, timedelta
 
s3 = boto3.client("s3")
 
BUCKET_NAME = "rahul-s3-automated-cleanup"
 
# --- Age threshold ---
# For testing, use minutes so you can see results immediately.
# For final submission, switch to days=30 and remove the minutes line.
# AGE_THRESHOLD = timedelta(minutes=5)     # <-- TESTING value
AGE_THRESHOLD = timedelta(days=30)     # <-- FINAL SUBMISSION value
 
 
def lambda_handler(event, context):
    now = datetime.now(timezone.utc)
    deleted_objects = []
 
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=BUCKET_NAME)
 
    for page in page_iterator:
        if "Contents" not in page:
            continue
 
        for obj in page["Contents"]:
            key = obj["Key"]
            last_modified = obj["LastModified"]  # already timezone-aware (UTC)
 
            age = now - last_modified
            if age > AGE_THRESHOLD:
                s3.delete_object(Bucket=BUCKET_NAME, Key=key)
                deleted_objects.append(key)
                print(f"Deleted: {key} (age: {age})")
            else:
                print(f"Kept: {key} (age: {age})")
 
    print(f"Total objects deleted: {len(deleted_objects)}")
    print(f"Deleted object keys: {deleted_objects}")
 
    return {
        "statusCode": 200,
        "bucket": BUCKET_NAME,
        "deleted_count": len(deleted_objects),
        "deleted_objects": deleted_objects,
    }
