# Assignment 4 — Daily AWS Cost Alert Using Cost Explorer API and SNS

## Task

Build an automated alert when AWS spend exceeds a threshold, using the Cost Explorer API (`ce:GetCostAndUsage`) rather than the legacy CloudWatch Billing metric, publishing to SNS, and scheduled daily via EventBridge.

## Solution — Step by Step

### 1. Setup

8. SNS → Topics → Create topic → Type: Standard, Name: **aws-cost-alerts**, Create topic.
9. Open the topic → Create subscription → Protocol: Email → Endpoint: your email → Create subscription.
10. Check your inbox and click Confirm subscription.
11. Copy the Topic ARN — needed in the code below.
12. **COST WARNING:** each `ce:GetCostAndUsage` call costs roughly $0.01 (~Rs.1). Plan to invoke this manually only a handful of times.

![SNS topic creation](screenshots/01-sns-topic-create.png)
![SNS subscription confirmation](screenshots/02-sns-subscription-confirm.png)

### 2. Create the IAM Role

13. IAM → Roles → Create role → AWS service → Lambda → name **cost-alert-lambda-role**
14. Add inline policy → JSON → paste the policy below, replacing the SNS ARN placeholder with your real topic ARN → name it **CostAlertPolicy** → Create Role

**Inline policy JSON used:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CostExplorerReadOnly",
      "Effect": "Allow",
      "Action": "ce:GetCostAndUsage",
      "Resource": "*"
    },
    {
      "Sid": "SNSPublishPermissions",
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:xxxxxxxxxxxx:your-topic-name"
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

![IAM role inline policy](screenshots/03-iam-role-inline-policy.png)

### 3. Create the Lambda Function

15. Lambda → Create function → **Daily-cost-alert**, Python 3.14, existing role → **cost-alert-lambda-role** → Create function
16. Paste the code below, update `SNS_TOPIC_ARN` to your real ARN.
17. Confirm `THRESHOLD_USD = 0.01` is active (testing mode, guaranteed to trigger an alert), Deploy.
18. Configuration → General → Timeout: 30 seconds, Save.

**Full function code (`lambda_function.py`):**

```python
"""
Assignment 4: Daily AWS Cost Alert Using Cost Explorer API and SNS

Queries month-to-date UnblendedCost via the Cost Explorer API and publishes
an SNS alert if spend exceeds a threshold.

COST WARNING: each ce:GetCostAndUsage call costs approximately $0.01 (~Rs.1).
Test this only a handful of times manually. Do NOT leave a short/aggressive
EventBridge schedule running while you experiment -- attach the daily
schedule only once you're done testing.
"""
import boto3
from datetime import datetime, timezone

ce = boto3.client("ce")
sns = boto3.client("sns")

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:xxxxxxxxxxxx:your-topic-name"  # <-- CHANGE THIS

# For testing, use a tiny threshold (e.g. 0.01) to force an alert.
# For final submission, switch to a realistic threshold like 50.00.
THRESHOLD_USD = 0.01  # <-- TESTING value
# THRESHOLD_USD = 50.00  # <-- FINAL SUBMISSION value


def get_month_to_date_cost():
    today = datetime.now(timezone.utc).date()
    start_of_month = today.replace(day=1)

    # Cost Explorer's End date is exclusive, and must be after Start.
    # If today is the 1st, query yesterday through today so the range is valid.
    if today == start_of_month:
        end_date = today
        start_date = today
    else:
        start_date = start_of_month
        end_date = today

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.isoformat(),
            "End": end_date.isoformat(),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )

    results = response["ResultsByTime"]
    if not results:
        return 0.0

    amount = float(results[0]["Total"]["UnblendedCost"]["Amount"])
    return amount


def lambda_handler(event, context):
    current_spend = get_month_to_date_cost()
    print(f"Month-to-date UnblendedCost: ${current_spend:.4f}")

    alert_sent = False
    if current_spend > THRESHOLD_USD:
        message = (
            f"AWS Cost Alert: month-to-date spend is ${current_spend:.2f}, "
            f"which exceeds your threshold of ${THRESHOLD_USD:.2f}."
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="AWS Daily Cost Alert",
            Message=message,
        )
        alert_sent = True
        print("Threshold exceeded -- SNS alert published.")
    else:
        print("Spend is within threshold -- no alert sent.")

    return {
        "statusCode": 200,
        "current_spend_usd": current_spend,
        "threshold_usd": THRESHOLD_USD,
        "alert_sent": alert_sent,
    }
```

![Lambda function code pasted](screenshots/04-lambda-function-code.png)

### 4. Test It

1. Lambda → Test → Create new event → Event name: `ManualCostAlertTest` → invoke with empty `{}` test event, once → Save & Test
2. Check CloudWatch Logs for the printed month-to-date **UnblendedCost** value.
3. Check your email for the SNS cost alert (expected, since the $0.01 test threshold is essentially always exceeded).
4. Avoid re-testing more than 2-3 times total to keep API charges minimal

![Test — CloudWatch logs](screenshots/05-test-cloudwatch-logs.png)
![Test — SNS email alert](screenshots/06-test-sns-email-alert.png)

### 5. Create EventBridge Scheduler

5. EventBridge → Scheduler → Create Schedule → name **Daily_Cost_Alert** → Enter Description → Schedule Pattern: Recurring
   a. Minutes — 0
   b. Hours — 10
   c. Day of Month, Month, Year — *
   d. Day of week — ?
6. Next → Target: Lambda function → Choose created lambda function: **daily-cost-alert** → Next → Create rule.
7. Only attach this schedule once you're fully done testing, since it will trigger a billed API call every day.

![EventBridge scheduler creation](screenshots/07-eventbridge-scheduler-create.png)
![EventBridge scheduler target](screenshots/08-eventbridge-scheduler-target.png)
![EventBridge scheduler review](screenshots/09-eventbridge-scheduler-review.png)

### 6. Clean Up

8. Change `THRESHOLD_USD` back to a realistic value like 50.00 and Deploy — this is the final submission version.
9. Double-check the EventBridge rule is only scheduled daily, not more frequently.

### 7. Discussion Point

AWS Budgets is the fully managed alternative and requires no code at all for a simple threshold alert. A custom Lambda still wins when you need per-service cost breakdowns in the alert message, delivery to Slack/Teams instead of email, or anomaly-detection style logic (e.g. comparing today's spend rate against a trailing average) that Budgets' fixed thresholds can't express.
