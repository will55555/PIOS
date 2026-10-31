# Terraform (placeholder)

Filled in after step 1. Planned modules (planning notes §G4, architecture §4):
- `budgets` — $45 account budget, $30 on `project=pios-algo`, anomaly monitor, billing alarm
- `tenancy` — per-tenant KMS key, SSM paths `/pios-algo/<tenant>/{paper|live}/*`, runtime IAM role
- `serverless` — watchdog, fallback exit watcher, downloader, reconcile, EOD report; DynamoDB heartbeat/lease/flags; S3
- `engine` — ASG of 1, `capacity = "spot" | "ondemand"` (C-scheduled only after the profit gate passes)

No state, no tfvars and no keys in this repo.
