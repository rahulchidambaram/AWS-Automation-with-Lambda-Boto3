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
 
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:074610727045:aws-cost-alerts"
 
# For testing, use a tiny threshold (e.g. 0.01) to force an alert.
# For final submission, switch to a realistic threshold like 50.00.
THRESHOLD_USD = 0.01     # <-- TESTING value
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
