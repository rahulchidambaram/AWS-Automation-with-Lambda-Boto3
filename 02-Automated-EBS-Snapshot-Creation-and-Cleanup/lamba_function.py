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
RETENTION = timedelta(minutes=5)     # <-- TESTING value
# RETENTION = timedelta(days=30)     # <-- FINAL SUBMISSION value
 
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
