# Assignment 3 — Auto-Tagging EC2 Instances on Launch

## Task

Automatically tag newly launched EC2 instances for resource tracking, ownership, and cost allocation, triggered by an EventBridge rule on instance state change. Bonus: resolve the launching IAM user via CloudTrail.

## Solution — Step by Step

### 1. Launch an EC2 Instance

- Open the EC2 Console → Click Launch Instance.
- Configure:
  - Enter a name → Amazon Linux 2023 AMI → t2.micro
  - Choose existing key value pair → Required VPC → Auto assign Public IP → Select existing SG (Allows SSH, HTTP & HTTPS)
  - 8 GiB gp3
- Launch the instance.

Note: This instance will be used later to verify automatic tagging.

![EC2 instance launch](screenshots/01-ec2-instance-launch.png)

### 2. Create the IAM Role

1. IAM → Roles → Create role → AWS service → Lambda → name **EC2-autotag-lambda-role**
2. Add inline policy → JSON → paste the policy below as-is → name it **EC2AutoTagPolicy**.

**Inline policy JSON used:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2TaggingPermissions",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudTrailLookupForBonus",
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents"
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

![IAM role inline policy](screenshots/02-iam-role-inline-policy.png)

### 3. Create the Lambda Function

3. Lambda → Create function → **ec2-autotag-on-launch**, Python 3.14, existing role → **ec2-autotag-lambda-role**.
4. Paste the code below, Deploy.
5. Configuration → General configuration → Edit → Timeout: 15 seconds, Save.

**Full function code (`lambda_function.py`):**

```python
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
ENVIRONMENT_TAG_VALUE = "Dev"  # change to whatever makes sense for you


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
```

![Lambda function code pasted](screenshots/03-lambda-function-code.png)

### 4. Test It

6. Create a new Test Event. Give a name
7. Paste the below JSON in Event JSON. (Replace the instance-id from the created EC2)

```json
{
  "detail": {
    "instance-id": "i-xxxxxxxxxxxxxxxxx"
  }
}
```

8. Check CloudWatch Logs for the 'Tagged instance...' line (Logs → Log Management)

![Test — CloudWatch logs, step 1](screenshots/04-test-cloudwatch-logs-1.png)
![Test — CloudWatch logs, step 2](screenshots/05-test-cloudwatch-logs-2.png)

### 5. Configure EventBridge

1. Amazon EventBridge → Rules → Create rule
2. Go to Configure tab → Enter name: **AutoTagEC2Rule** & Description: **Automatically tags EC2 instances when they enter the running state** → Event bus: default → Rule type: Rule with an event pattern.
3. Go to Build tab → In Events: AWS Service Events → Drag **EC2 Instance State Change Notification** to triggering event → Make sure the Event Pattern looks like the below JSON:

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["running"]
  }
}
```

4. Drag **Lambda function** to Targets → Click on No resource selected in Lambda → Target in this account → Choose existing role: **EC2-autotag-lambda-role** → Leave all other settings as default.
5. Create rule.

![EventBridge rule configure](screenshots/06-eventbridge-rule-configure.png)
![EventBridge rule pattern](screenshots/07-eventbridge-rule-pattern.png)
![EventBridge rule target](screenshots/08-eventbridge-rule-target.png)

**Final Output**

![Final output — instance tags, view 1](screenshots/09-final-output-tags-1.png)
![Final output — instance tags, view 2](screenshots/10-final-output-tags-2.png)

### 6. Clean Up

6. Terminate the created instances, Amazon EventBridge, Lambda & IAM Roles
7. Confirm it's terminated before logging out.

### 7. Discussion Point

The bonus CloudTrail lookup is a common interview scenario because it demonstrates correlating an EC2 lifecycle event with the IAM identity that caused it — useful for real ownership/cost-accountability tagging rather than a generic default tag.
