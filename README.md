# AWS Lambda Automation using Boto3

A collection of hands-on AWS automation projects built using AWS Lambda, Python (Boto3), IAM, Amazon EventBridge, Amazon SNS, Amazon S3, Amazon EC2, and Amazon EBS. These projects demonstrate how to automate common cloud operations, improve operational efficiency, and implement infrastructure best practices using serverless architectures. The repository is based on four practical automation assignments covering storage management, backup automation, resource tagging, and AWS cost monitoring.

### Each assignment is self-contained and includes its own **README.md** with detailed setup instructions, architecture, implementation steps, testing procedure, and screenshots.

## Assignments

1. Automated S3 Bucket Cleanup
2. Automated EBS Snapshot Creation and Cleanup
3. Auto Tagging EC2 Instances
4. Daily AWS Cost Alert using Cost Explorer API and SNS

Each assignment contains:

- `lambda_function.py` – AWS Lambda source code
- IAM policy JSON files
- Screenshots for setup, testing, and results
- `README.md` – Complete implementation guide and documentation

---
These projects demonstrate practical usage of AWS services commonly used in production environments and provide a strong foundation for learning serverless automation.


## 📂 Repository Structure

```text
│   AWS Automation with Lambda & Boto3.docx
│   README.md
│   
├───01-Automated-S3-Bucket-Cleanup
│   │   iam_policy.json
│   │   lamba_function.py
│   │   README.md
│   │   
│   └───screenshots
│           1.Set-budget-limit.png
│           10.After_cleanup.png
│           2.Files-uploaded.png
│           3.Inline-policies.png
│           4.Permission-policies.png
│           5.IAM_Role.png
│           6.Lambda.png
│           7.Lambda_func.png
│           8.Test.png
│           9.Before_Deletion.png
│           
├───02-Automated-EBS-Snapshot-Creation-and-Cleanup
│   │   CustomTrustPolicy_EventBridge.json
│   │   iam_policy-EBS.json
│   │   iam_policy-EventBridge.json
│   │   lambda_function.py
│   │   README.md
│   │   
│   └───screenshots
│           1.Network-setup.png
│           10.Cloud-watch-logs.png
│           11.EventBridge.png
│           2.Volume-setup.png
│           3.EC2.png
│           4.Volume-ID-EBS.png
│           5.IAM-EBS-Role.png
│           6.Lambda-Code.png
│           7.Lambda-config.png
│           8.Test-events.png
│           9.Snapshots.png
│           9A.Snapshot-owner.png
│           
├───03-Auto-Tagging-EC2-Instances-on-Launch
│   │   iam_policy.json
│   │   lambda_function.py
│   │   README.md
│   │   
│   └───screenshots
│           1.EC2.png
│           2.IAM-Role.png
│           3.Lambda-func.png
│           4.Logs.png
│           5.EventBridge-Rule.png
│           5.EventBridge.png
│           6.EventBridge-Targets.png
│           7.AutoTag-Output.png
│           8.NewEC2-Autotag.png
│           
└───04-Cost-Alert-SNS
    │   iam_policy.json
    │   lambda_function.py
    │   README.md
    │   
    └───screenshots
           1.SNS.png
           2.IAM-Role.png
           3.Lambda-func.png
           4.Test-CostAlert.png
           5.EventBridge.png
           6.Schedules.png
```
