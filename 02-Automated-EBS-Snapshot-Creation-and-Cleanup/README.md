# Assignment 2 — Automated EBS Snapshot Creation and Cleanup

## Task

Automate EBS volume backups: create a snapshot of a specified volume, tag it, and delete snapshots older than a retention period, scheduled weekly via EventBridge.

## Solution — Step by Step

### 1. Setup

- Login to the AWS Management Console → Search for EC2 → Click **Launch Instance** → Enter a Name **"EBS-Backup-Server"** → Choose **Amazon Linux AMI** → Instance Type: **t2.micro** → Create or select an existing key pair.
- Find the reference Network settings below. (Allow SSH)

<img width="975" height="521" alt="image" src="https://github.com/user-attachments/assets/e4811b5b-308b-40d2-a4f1-b97e8f72184a" />


- Under Configure Storage:
   - Volume Type: gp3 | Size: 8 GiB
- Click Launch Instance.

<img width="975" height="394" alt="image" src="https://github.com/user-attachments/assets/5cb62dc5-634a-47f3-9484-7d1160feb0fc" />


- EC2 → Volumes (left sidebar) → find the volume attached to your instance → copy its Volume ID (`vol-0b3c79c9f6f3491f7`).


<img width="975" height="384" alt="image" src="https://github.com/user-attachments/assets/82181a84-4228-431e-9237-134bf0b23b7e" />



### 2. Create the IAM Role for Lambda EBS Snapshot

- Console → IAM → Roles → Create role.
- Trusted entity: AWS service → Use case: Lambda.
- Next → Create Inline Policy → JSON → paste the policy below as-is → name it **EBSSnapshotPolicy** → Role name: **ebs-snapshot-lambda-role** → Create Role

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

<img width="975" height="372" alt="image" src="https://github.com/user-attachments/assets/135a2a01-eb4c-4b4a-8309-d09a82a4a704" />


### 3. Create the IAM Role for Event Bridge Scheduler

- Go to Roles → Create role → Choose Custom trust policy.
- Replace the default policy with the following:

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

- Next → Create Inline Policy → JSON → paste the policy below as-is → Create Role

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

<img width="975" height="377" alt="image" src="https://github.com/user-attachments/assets/0542cf34-3b45-4451-a512-d8022efa3f39" />


### 4. Create the Lambda Function

- Lambda → Create function → Author from scratch → Function name: **ebs-snapshot-backup-cleanup**, Python 3.14, Configure custom execution role (choose existing role) → **ebs-snapshot-lambda-role** → Create function
- Paste the code below (Code Source).
- Confirm `RETENTION = timedelta(minutes=1)` is active for testing, Deploy.
- Configuration → General → Timeout: 30 seconds, Save.

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

<img width="975" height="411" alt="image" src="https://github.com/user-attachments/assets/3228840b-eb1a-407e-bc38-df1df1337249" />

<img width="975" height="373" alt="image" src="https://github.com/user-attachments/assets/e798a852-067c-4a6a-b452-014a4bbb061d" />


### 5. Test It

- Lambda → Test → Event name: **ManualSnapshotTest** → invoke with empty `{}` test event. Save and Test

<img width="975" height="338" alt="image" src="https://github.com/user-attachments/assets/b9d7f9b5-e829-46a4-9702-452ba3a185e7" />

<img width="975" height="386" alt="image" src="https://github.com/user-attachments/assets/6db9f2f0-cc9e-42f2-9505-da0d101e12bb" />


- EC2 → Snapshots (left sidebar) → refresh, confirm the new snapshot appears tagged **CreatedBy=Lambda-Backup**.
- Wait 5+ minutes, invoke Test again — this second run should delete the first snapshot (now older than the 5-minute testing retention) while keeping the newest one.

<img width="975" height="363" alt="image" src="https://github.com/user-attachments/assets/a1d8f301-29da-4ee7-9584-a3acaec9f286" />


- Check CloudWatch Logs for the created/deleted snapshot ID lines.

<img width="975" height="377" alt="image" src="https://github.com/user-attachments/assets/92622129-0787-4438-88e4-e7194aad1859" />

<img width="975" height="388" alt="image" src="https://github.com/user-attachments/assets/60b7d580-a9ba-4c32-8740-83cc1cd9a5ed" />


### 6. Configure EventBridge Scheduler

EventBridge Scheduler is the recommended AWS service for recurring scheduled tasks and replaces the need for creating a scheduled EventBridge Rule.

- Go to Amazon EventBridge → Under Scheduler (Schedule) → Create Schedule
- Enter Schedule Name (**Weekly-EBS-Backup**) & Description → Recurring Schedule → Cron-based Schedule → `cron(0 10 ? * SUN *)` → Flexible Time Window (Off)

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/41280c9b-7d7b-4521-a17e-aa3caf8169dc" />


- Select Target → AWS Lambda → Select the previously created Lambda function → Use the existing role → **EventBridgeSchedulerLambdaRole**
- Review and Create Schedule

<img width="975" height="382" alt="image" src="https://github.com/user-attachments/assets/09a7e53d-1ae8-4f6e-9261-52726070d40c" />


### 7. Clean Up

- Change `RETENTION` back to `timedelta(days=30)` and Deploy — this is the final submission version.
- Delete any leftover test snapshots manually from EC2
- Snapshots (Actions → Delete snapshot).
- Terminate the throwaway EC2 instance used for the volume.

### 8. Discussion Point

AWS Data Lifecycle Manager (DLM) can automatically create and delete EBS snapshots based on retention policies without writing code. A custom Lambda is still worth it when you need retention logic DLM can't express (e.g. keep last 'N' snapshots per environment tag), need to copy snapshots cross-account/cross-region as part of the same workflow, or want to fire a custom notification (Slack/SNS) tied to backup success or failure.
