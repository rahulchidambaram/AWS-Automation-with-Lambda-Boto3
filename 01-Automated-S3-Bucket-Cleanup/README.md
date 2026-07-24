# Assignment 1 — Automated S3 Bucket Cleanup (Objects Older Than 30 Days)

## Task

Automate deletion of stale objects in an S3 bucket: delete files older than 30 days in a specific bucket, using a Lambda function (Python 3.14 + Boto3) with a least-privilege IAM role.

## Solution — Step by Step

### 1. Setup

1. Console → S3 → Create bucket. Name it something unique (e.g. `rc-lambda-cleanup-test-<random numbers>`), region `us-east-1`.
2. Leave all defaults (Block Public Access ON), click **Create bucket**.
3. Upload 3-4 small test files (any `.txt` files work) into the bucket.

![S3 bucket with test files uploaded](screenshots/02-s3-bucket-test-files.png)

### 2. Create the IAM Role

4. Console → IAM → Roles → Create role.
5. Trusted entity: AWS service → Use case: Lambda.
6. Skip attaching a managed policy for now, name it **s3-cleanup-lambda-role**, Create role.
7. Open the role → Add permissions → Create inline policy → JSON tab.
8. Click Add permissions → Attach policies → Add → **AWSLambdaBasicExecutionRole**
9. Paste the policy below, replacing `your-bucket-name-here` in both ARNs with your actual bucket name.
10. Name the policy **S3CleanupInlinePolicy**, Create policy.

**Inline policy JSON used:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::rahul-s3-automated-cleanup"
    },
    {
      "Sid": "ObjectActions",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::rahul-s3-automated-cleanup/*"
    }
  ]
}
```

![IAM inline policy JSON step 1](screenshots/03-iam-role-inline-policy-json-1.png)
![IAM inline policy JSON step 2](screenshots/04-iam-role-inline-policy-json-2.png)
![IAM inline policy JSON step 3](screenshots/05-iam-role-inline-policy-json-3.png)

### 3. Create the Lambda Function

11. Console → Lambda → Create function → Author from scratch.
12. Name: **s3-stale-object-cleanup**, Runtime: Python 3.14.
13. Under 'General' → 'Custom execution role' → Choose an existing role → select **s3-cleanup-lambda-role**.
14. Create function.
15. In the code editor, delete the placeholder code and paste the code below.
16. Confirm `AGE_THRESHOLD = timedelta(minutes=5)` is active (testing mode), then Deploy.

**Full function code (`lambda_function.py`):**

```python
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
AGE_THRESHOLD = timedelta(minutes=5)  # <-- TESTING value
# AGE_THRESHOLD = timedelta(days=30)  # <-- FINAL SUBMISSION value


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
```

![Lambda function code pasted, step 1](screenshots/06-lambda-function-code-1.png)
![Lambda function code pasted, step 2](screenshots/07-lambda-function-code-2.png)
![Lambda function code pasted, step 3](screenshots/08-lambda-function-code-3.png)

### 4. Test It

17. Click Test → Create new test event → name it **manual-auto-cleanup-test** → keep the default empty JSON `{}` → Save.
18. Click Test again to invoke the function.
19. In Lambda → Go to the Monitor tab → View CloudWatch logs → open the latest log stream to see the `Kept:`/`Deleted:` lines.
20. Go back to S3 and refresh the bucket to confirm the expected files remain.
21. To actually see a deletion happen: temporarily set `AGE_THRESHOLD = timedelta(seconds=10)`, wait 15 seconds, and re-test.

![Test event setup](screenshots/09-test-event-setup.png)

**Before Deletion**

![CloudWatch logs before deletion](screenshots/10-before-deletion-cloudwatch-logs.png)
![S3 bucket before deletion](screenshots/11-before-deletion-s3-bucket.png)

**After Clean-up**

![CloudWatch logs after cleanup](screenshots/12-after-cleanup-cloudwatch-logs.png)
![S3 bucket after cleanup](screenshots/13-after-cleanup-s3-bucket.png)

### 5. Clean Up

22. Change `AGE_THRESHOLD` back to `timedelta(days=30)` and Deploy again.
23. Delete the test bucket (or its contents) once you're done capturing screenshots, to avoid any storage charges.

### 6. Discussion Point

In production, S3 Lifecycle Rules can expire objects after 'N' days natively, with zero code and no compute cost. I'd reach for a Lambda-based approach instead when the deletion logic needs conditions Lifecycle Rules can't express — for example, deleting based on object naming patterns/prefixes with custom logic, cross-referencing against another service (like checking a DynamoDB table before deleting), or triggering a notification/audit trail alongside the deletion.
