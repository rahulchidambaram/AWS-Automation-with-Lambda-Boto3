# Assignment 1 — Automated S3 Bucket Cleanup (Objects Older Than 30 Days)

## Task

Automate deletion of stale objects in an S3 bucket: delete files older than 30 days in a specific bucket, using a Lambda function (Python 3.14 + Boto3) with a least-privilege IAM role.

## Best Practices
Create a monthly AWS Budget with a $1 limit to receive email notifications and avoid unexpected AWS charges.

### Steps:
1. Sign in to the AWS Management Console. 
2. Search for Billing and Cost Management. 
3. Select Budgets from the left navigation pane.
4. Choose Cost Budget.
5. Give a Budget name, Budget period, Recurring Budget: Yes, Budget amount: $1. Leave the remaining options as default.
6. Create an Alert, add notification, Enter your email address.
7. Create the budget.

<img width="975" height="195" alt="image" src="https://github.com/user-attachments/assets/e6918076-d24c-4009-bb1d-6b127aa65a61" />


## Solution — Step by Step

### 1. Setup

- Console → S3 → Create bucket. Name it something unique (e.g. `rc-lambda-cleanup-test-<random numbers>`), region `us-east-1`.
- Leave all defaults (Block Public Access ON), click **Create bucket**.
- Upload 3-4 small test files (any `.txt` files work) into the bucket.

<img width="975" height="270" alt="image" src="https://github.com/user-attachments/assets/7ccfda20-50da-44d6-a133-814097da4dcc" />


### 2. Create the IAM Role

- Console → IAM → Roles → Create role.
- Trusted entity: AWS service → Use case: Lambda.
- Skip attaching a managed policy for now, name it **s3-cleanup-lambda-role**, Create role.
- Open the role → Add permissions → Create inline policy → JSON tab.
- Click Add permissions → Attach policies → Add → **AWSLambdaBasicExecutionRole**
- Paste the policy below, replacing `your-bucket-name-here` in both ARNs with your actual bucket name.
- Name the policy **S3CleanupInlinePolicy**, Create policy.

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
 
<img width="975" height="391" alt="image" src="https://github.com/user-attachments/assets/e37da2f2-6246-4ed1-a384-f45ff787ae01" />

<img width="975" height="266" alt="image" src="https://github.com/user-attachments/assets/60216776-28ee-4cce-b6ee-75a227ef7690" />

<img width="975" height="239" alt="image" src="https://github.com/user-attachments/assets/fe60ae3f-0360-422c-97fb-740b4650bd34" />
 

### 3. Create the Lambda Function

- Console → Lambda → Create function → Author from scratch.
- Name: **s3-stale-object-cleanup**, Runtime: Python 3.14.
- Under 'General' → 'Custom execution role' → Choose an existing role → select **s3-cleanup-lambda-role**.
- Create function.
- In the code editor, delete the placeholder code and paste the code below.
- Confirm `AGE_THRESHOLD = timedelta(minutes=5)` is active (testing mode), then Deploy.

**Full function code (`lambda_function.py`):**

```python
"""
Deletes objects in a given S3 bucket whose LastModified timestamp is older
than a configurable age threshold.

FOR TESTING: set AGE_THRESHOLD_MINUTES (e.g. 5) via the Lambda env var
or the fallback below, so you don't have to wait 30 real days to see it work.

"""
import boto3
from datetime import datetime, timezone, timedelta

s3 = boto3.client("s3")

BUCKET_NAME = "rahul-s3-automated-cleanup"

# --- Age threshold ---
# For testing, use minutes so you can see results immediately.
# For final submission, switch to days=30 and remove the minutes line.
# AGE_THRESHOLD = timedelta(minutes=5)  # <-- TESTING value
AGE_THRESHOLD = timedelta(days=30)  # <-- FINAL SUBMISSION value


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

<img width="809" height="621" alt="image" src="https://github.com/user-attachments/assets/548cf3be-dccd-4fa8-8b81-4e171a6af0f3" />


### 4. Test It

- Click Test → Create new test event → name it **manual-auto-cleanup-test** → keep the default empty JSON `{}` → Save.
- Click Test again to invoke the function.
- In Lambda → Go to the Monitor tab → View CloudWatch logs → open the latest log stream to see the `Kept:`/`Deleted:` lines.
- Go back to S3 and refresh the bucket to confirm the expected files remain.
- To actually see a deletion happen: temporarily set `AGE_THRESHOLD = timedelta(seconds=10)`, wait 15 seconds, and re-test.

<img width="975" height="399" alt="image" src="https://github.com/user-attachments/assets/b9258c92-1b60-466c-9ad4-fc0e68f02176" />


**Before Deletion**

<img width="785" height="632" alt="image" src="https://github.com/user-attachments/assets/caefbaf2-b177-4e77-99c8-08ca0d39d76d" />


**After Clean-up**

<img width="791" height="613" alt="image" src="https://github.com/user-attachments/assets/01220f22-ed3e-497c-a636-a5c908396933" />


### 5. Clean Up

- Change `AGE_THRESHOLD` back to `timedelta(days=30)` and Deploy again.
- Delete the test bucket (or its contents) once you're done capturing screenshots, to avoid any storage charges.

### 6. Discussion Point

In production, S3 Lifecycle Rules can expire objects after 'N' days natively, with zero code and no compute cost. I'd reach for a Lambda-based approach instead when the deletion logic needs conditions Lifecycle Rules can't express — for example, deleting based on object naming patterns/prefixes with custom logic, cross-referencing against another service (like checking a DynamoDB table before deleting), or triggering a notification/audit trail alongside the deletion.
