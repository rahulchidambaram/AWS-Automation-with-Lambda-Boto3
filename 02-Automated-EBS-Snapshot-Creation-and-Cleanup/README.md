# Assignment 2 — Automated EBS Snapshot Creation and Cleanup

## Task

Automate EBS volume backups: create a snapshot of a specified volume, tag it, and delete snapshots older than a retention period, scheduled weekly via EventBridge.

## Solution — Step by Step

### 1. Setup

1. Login to the AWS Management Console → Search for EC2 → Click **Launch Instance** → Enter a Name **"EBS-Backup-Server"** → Choose **Amazon Linux AMI** → Instance Type: **t2.micro** → Create or select an existing key pair.
2. Find the reference Network settings below. (Allow SSH)

![EC2 network settings](screenshots/01-ec2-network-settings.png)

3. Under Configure Storage:
   - Volume Type: gp3 | Size: 8 GiB
4. Click Launch Instance.

![EC2 launch configured](screenshots/02-ec2-launch-configured.png)

5. EC2 → Volumes (left sidebar) → find the volume attached to your instance → copy its Volume ID (`vol-0b3c79c9f6f3491f7`).

![EBS volume ID](screenshots/03-ebs-volume-id.png)

### 2. Create the IAM Role for Lambda EBS Snapshot

6. Console → IAM → Roles → Create role.
7. Trusted entity: AWS service → Use case: Lambda.
8. Next → Create Inline Policy → JSON → paste the policy below as-is → name it **EBSSnapshotPolicy** → Role name: **ebs-snapshot-lambda-role** → Create Role

**Inline policy JSON used:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EBSSnapshotPermissions",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:DescribeSnapshots",
        "ec2:DeleteSnapshot",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaLogging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

![IAM role for EBS snapshot policy](screenshots/04-iam-role-ebs-snapshot-policy.png)

### 3. Create the IAM Role for Event Bridge Scheduler

1. Go to Roles → Create role → Choose Custom trust policy.
2. Replace the default policy with the following:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "scheduler.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. Next → Create Inline Policy → JSON → paste the policy below as-is → Create Role

**Inline policy JSON used:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeLambda",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:ap-south-1:074610727045:function:ebs-snapshot-backup-cleanup"
    }
  ]
}
```

![IAM role for EventBridge Scheduler](screenshots/05-iam-role-eventbridge-scheduler.png)

### 4. Create the Lambda Function

4. Lambda → Create function → Author from scratch → Function name: **ebs-snapshot-backup-cleanup**, Python 3.14, Configure custom execution role (choose existing role) → **ebs-snapshot-lambda-role** → Create function
5. Paste the code below (Code Source).
6. Confirm `RETENTION = timedelta(minutes=1)` is active for testing, Deploy.
7. Configuration → General → Timeout: 30 seconds, Save.

**Full function code (`lambda_function.py`):**

```python
"""
Assignment 2: Automated EBS Snapshot Creation and Cleanup

- Creates a new snapshot of a given EBS volume, tagged CreatedBy=Lambda-Backup.
- Lists all snapshots owned by this account with that tag, and deletes any
  older than the retention period.

Trigger this manually for testing, then attach a weekly EventBridge schedule.
"""
import boto3
from datetime import datetime, timezone, timedelta

ec2 = boto3.client("ec2")

VOLUME_ID = "vol-0b3c79c9f6f3491f7"

# For testing use a short retention (e.g. minutes); switch to 30 days for submission.
RETENTION = timedelta(minutes=5)  # <-- TESTING value
# RETENTION = timedelta(days=30)  # <-- FINAL SUBMISSION value

TAG_KEY = "CreatedBy"
TAG_VALUE = "Lambda-Backup"


def lambda_handler(event, context):
    now = datetime.now(timezone.utc)

    # 1. Create a new snapshot of the volume
    snapshot = ec2.create_snapshot(
        VolumeId=VOLUME_ID,
        Description=f"Automated backup of {VOLUME_ID} via Lambda",
        TagSpecifications=[
            {
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": TAG_KEY, "Value": TAG_VALUE},
                    {"Key": "SourceVolume", "Value": VOLUME_ID},
                ],
            }
        ],
    )
    new_snapshot_id = snapshot["SnapshotId"]
    print(f"Created snapshot: {new_snapshot_id}")

    # 2. List all snapshots owned by this account with our tag
    response = ec2.describe_snapshots(
        OwnerIds=["self"],
        Filters=[{"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]}],
    )

    deleted_snapshots = []
    for snap in response["Snapshots"]:
        snap_id = snap["SnapshotId"]
        start_time = snap["StartTime"]  # timezone-aware

        # Never delete the snapshot we just created in this same run
        if snap_id == new_snapshot_id:
            continue

        age = now - start_time
        if age > RETENTION:
            ec2.delete_snapshot(SnapshotId=snap_id)
            deleted_snapshots.append(snap_id)
            print(f"Deleted old snapshot: {snap_id} (age: {age})")
        else:
            print(f"Kept snapshot: {snap_id} (age: {age})")

    print(f"Created: {new_snapshot_id}")
    print(f"Deleted snapshots: {deleted_snapshots}")

    return {
        "statusCode": 200,
        "created_snapshot": new_snapshot_id,
        "deleted_snapshots": deleted_snapshots,
    }
```

![Lambda function code pasted, step 1](screenshots/06-lambda-function-code-1.png)
![Lambda function code pasted, step 2](screenshots/07-lambda-function-code-2.png)

### 5. Test It

8. Lambda → Test → Event name: **ManualSnapshotTest** → invoke with empty `{}` test event. Save and Test

![Test invoke, step 1](screenshots/08-test-invoke-1.png)
![Test invoke, step 2](screenshots/09-test-invoke-2.png)

9. EC2 → Snapshots (left sidebar) → refresh, confirm the new snapshot appears tagged **CreatedBy=Lambda-Backup**.
10. Wait 5+ minutes, invoke Test again — this second run should delete the first snapshot (now older than the 5-minute testing retention) while keeping the newest one.

![Second run — old snapshot deleted](screenshots/10-second-run-snapshot-deleted.png)

11. Check CloudWatch Logs for the created/deleted snapshot ID lines.

![CloudWatch logs, step 1](screenshots/11-cloudwatch-logs-1.png)
![CloudWatch logs, step 2](screenshots/12-cloudwatch-logs-2.png)

### 6. Configure EventBridge Scheduler

EventBridge Scheduler is the recommended AWS service for recurring scheduled tasks and replaces the need for creating a scheduled EventBridge Rule.

1. Go to Amazon EventBridge → Under Scheduler (Schedule) → Create Schedule
2. Enter Schedule Name (**Weekly-EBS-Backup**) & Description → Recurring Schedule → Cron-based Schedule → `cron(0 10 ? * SUN *)` → Flexible Time Window (Off)

![EventBridge schedule creation](screenshots/13-eventbridge-schedule-create.png)

3. Select Target → AWS Lambda → Select the previously created Lambda function → Use the existing role → **EventBridgeSchedulerLambdaRole**
4. Review and Create Schedule

![EventBridge schedule review](screenshots/14-eventbridge-schedule-review.png)

### 7. Clean Up

5. Change `RETENTION` back to `timedelta(days=30)` and Deploy — this is the final submission version.
6. Delete any leftover test snapshots manually from EC2
7. Snapshots (Actions → Delete snapshot).
8. Terminate the throwaway EC2 instance used for the volume.

### 8. Discussion Point

AWS Data Lifecycle Manager (DLM) can automatically create and delete EBS snapshots based on retention policies without writing code. A custom Lambda is still worth it when you need retention logic DLM can't express (e.g. keep last 'N' snapshots per environment tag), need to copy snapshots cross-account/cross-region as part of the same workflow, or want to fire a custom notification (Slack/SNS) tied to backup success or failure.
