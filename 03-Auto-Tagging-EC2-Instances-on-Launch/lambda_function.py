"""
Assignment 3: Auto-Tagging EC2 Instances on Launch
 
Triggered by an EventBridge rule matching:
  source: aws.ec2
  detail-type: "EC2 Instance State-change Notification"
  detail.state: "running"
 
Tags the newly running instance with LaunchDate and Owner.
 
BONUS: looks up the IAM principal who launched the instance via CloudTrail
(RunInstances event) and uses that as the Owner tag when available.
"""
 
import boto3
from datetime import datetime, timezone, timedelta
 
ec2 = boto3.client("ec2")
cloudtrail = boto3.client("cloudtrail")
 
DEFAULT_OWNER = "unknown"
ENVIRONMENT_TAG_VALUE = "Dev"
 
 
def get_launching_user(instance_id):
    """
    Bonus: search recent CloudTrail events for the RunInstances call
    that launched this instance, and return the calling principal's
    ARN/username. Falls back to DEFAULT_OWNER if nothing is found
    (CloudTrail can take a few minutes to index events).
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
 
        response = cloudtrail.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "EventName", "AttributeValue": "RunInstances"}
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=20,
        )
 
        for event in response.get("Events", []):
            if instance_id in event.get("Resources", []) or instance_id in event.get(
                "CloudTrailEvent", ""
            ):
                username = event.get("Username", DEFAULT_OWNER)
                return username
 
    except Exception as e:
        print(f"Could not look up CloudTrail event: {e}")
 
    return DEFAULT_OWNER
 
 
def lambda_handler(event, context):
    detail = event.get("detail", {})
    instance_id = detail.get("instance-id")
 
    if not instance_id:
        print("No instance-id found in event, exiting.")
        return {"statusCode": 400, "message": "No instance-id in event"}
 
    launch_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    owner = get_launching_user(instance_id)
 
    ec2.create_tags(
        Resources=[instance_id],
        Tags=[
            {"Key": "LaunchDate", "Value": launch_date},
            {"Key": "Environment", "Value": ENVIRONMENT_TAG_VALUE},
            {"Key": "Owner", "Value": owner},
        ],
    )
 
    print(f"Tagged instance {instance_id} with LaunchDate={launch_date}, Owner={owner}")
 
    return {
        "statusCode": 200,
        "instance_id": instance_id,
        "launch_date": launch_date,
        "owner": owner,
    }
