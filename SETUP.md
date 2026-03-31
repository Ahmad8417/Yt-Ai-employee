# AI Employee - Silver Tier Setup Guide

Complete setup instructions for Gmail auto-reply + LinkedIn auto-post system.

## Prerequisites

- Python 3.8+
- Gmail account
- (Optional) LinkedIn Developer account for auto-posting

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Google API client libraries (for Gmail)
- Watchdog (file system monitoring)
- Schedule + croniter (task scheduling)
- Requests (for LinkedIn API)

---

## Step 2: Gmail Setup

### 2.1 Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop application"
   - Name: "AI Employee Gmail Watcher"
   - Click "Create"
5. Download the JSON file
6. **Rename it to `credentials.json` and place in project root**

### 2.2 Configure Gmail App

1. Go to [Google Account Permissions](https://myaccount.google.com/connections)
2. Ensure your app has access

### 2.3 First Run (Authentication)

```bash
python AI_Employee_Vault/gmail_watcher.py --vault ./AI_Employee_Vault --credentials ./credentials.json
```

**What happens:**
1. Browser opens automatically
2. Sign in with your Google account
3. Grant permissions (Gmail read/send/modify)
4. Token is saved to `token.pickle` for future runs

### 2.4 Test Gmail Watcher

```bash
# Check once
python AI_Employee_Vault/gmail_watcher.py

# Run as daemon (checks every 2 minutes)
python AI_Employee_Vault/gmail_watcher.py --daemon --interval 120
```

---

## Step 3: SMTP Configuration (Email Sending)

For the Email MCP to send emails, you need SMTP credentials.

### 3.1 Gmail SMTP Setup

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in if required
3. Select "Mail" as app
4. Select "Other (Custom name)" as device
5. Name it: "AI Employee"
6. Click "Generate"
7. **Copy the 16-character password**

### 3.2 Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in:
   ```
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password-here  # NOT your regular password
   ```

3. Load environment variables:
   ```bash
   # Windows PowerShell
   $env:SMTP_USERNAME="your-email@gmail.com"
   $env:SMTP_PASSWORD="your-app-password"

   # Or use python-dotenv
   python -c "from dotenv import load_dotenv; load_dotenv()"
   ```

---

## Step 4: LinkedIn Setup (Optional)

LinkedIn auto-posting requires API credentials.

### 4.1 LinkedIn Developer Portal

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Create an app
3. Request access to "Share on LinkedIn" product
4. Get OAuth 2.0 tokens

### 4.2 Configure LinkedIn

Edit `AI_Employee_Vault/Config/linkedin_config.json`:

```json
{
  "posting_enabled": true,
  "api_credentials": {
    "access_token": "your-access-token",
    "user_id": "your-user-id"
  }
}
```

### 4.3 Test LinkedIn Watcher

```bash
# Generate a post
python AI_Employee_Vault/linkedin_watcher.py generate

# Queue a post for approval
python AI_Employee_Vault/linkedin_watcher.py queue

# Schedule 7 days of posts
python AI_Employee_Vault/linkedin_watcher.py schedule --days 7
```

---

## Step 5: Approval Workflow Setup

The HITL (Human-in-the-Loop) system uses folder-based approvals.

### 5.1 How It Works

1. AI creates requests in `/Pending_Approval`
2. You review and move to `/Approved` or `/Rejected`
3. Scheduler processes approved items

### 5.2 Test Approval Workflow

```bash
# Create a test approval request
python AI_Employee_Vault/approval_workflow.py create-request \
    --action-type send_email \
    --details '{"to":"test@example.com","subject":"Test"}'

# List pending approvals
python AI_Employee_Vault/approval_workflow.py list-pending

# Approve a request
python AI_Employee_Vault/approval_workflow.py approve --request-id EMAIL_20260330_123456

# Execute approved items
python AI_Employee_Vault/approval_workflow.py check-approved --execute
```

---

## Step 6: Scheduler Setup

### 6.1 View Jobs

```bash
python AI_Employee_Vault/scheduler.py list
```

### 6.2 Enable Jobs

```bash
# Enable Gmail checking every 5 minutes
python AI_Employee_Vault/scheduler.py enable --job gmail_check

# Enable daily briefing at 8 AM
python AI_Employee_Vault/scheduler.py enable --job daily_briefing

# Enable LinkedIn posting on Mondays
python AI_Employee_Vault/scheduler.py enable --job linkedin_post
```

### 6.3 Run Scheduler Daemon

```bash
python AI_Employee_Vault/scheduler.py daemon
```

### 6.4 Windows Task Scheduler Integration

```bash
# Generate PowerShell command for Windows Task Scheduler
python AI_Employee_Vault/scheduler.py windows-task --job gmail_check
```

Copy the output and run in PowerShell as Administrator.

---

## Step 7: Configure Gmail Auto-Reply (Optional)

Edit `AI_Employee_Vault/Config/gmail_config.json`:

```json
{
  "auto_reply_enabled": true,
  "templates": {
    "general": "Thank you for your email. I'll get back to you shortly.\n\nBest regards"
  },
  "working_hours_only": true,
  "timezone": "America/New_York"
}
```

**Note:** The current implementation creates action files. Full auto-reply requires additional integration with the `send_reply()` method.

---

## Quick Start Commands

### Daily Operation

```bash
# 1. Check Gmail for new emails
python AI_Employee_Vault/gmail_watcher.py

# 2. Process approved actions
python AI_Employee_Vault/approval_workflow.py check-approved --execute

# 3. Update dashboard
python .claude/skills/process-vault.py update-dashboard

# 4. Generate LinkedIn content
python AI_Employee_Vault/linkedin_watcher.py generate
```

### Using Silver Tier Skill

```bash
# Check Gmail
python .claude/skills/silver-tier.py check-gmail

# Generate LinkedIn post
python .claude/skills/silver-tier.py generate-linkedin --category business_update

# Queue LinkedIn post
python .claude/skills/silver-tier.py queue-linkedin

# Create plan for a task
python .claude/skills/silver-tier.py create-plan

# Check approved items
python .claude/skills/silver-tier.py check-approved
```

---

## Troubleshooting

### Issue: "No credentials provided"

**Fix:** Ensure `credentials.json` exists in project root or set `GMAIL_CREDENTIALS_PATH` env var.

### Issue: "SMTP credentials not set"

**Fix:** Set `SMTP_USERNAME` and `SMTP_PASSWORD` environment variables.

### Issue: OAuth consent screen error

**Fix:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services > OAuth consent screen
3. Add your email as a test user
4. Or click "Publish App" to make it external

### Issue: "token.pickle not created"

**Fix:** Delete any existing `token.pickle` and re-run authentication.

### Issue: LinkedIn posts not actually posting

**Expected:** The current implementation queues posts for manual review. Actual posting to LinkedIn requires API credentials and additional implementation.

---

## File Structure

```
.
├── credentials.json          # Gmail OAuth credentials
├── token.pickle             # Saved OAuth token (auto-created)
├── .env                     # Environment variables (copy from .env.example)
├── requirements.txt         # Python dependencies
├── SETUP.md                 # This file
├── AI_Employee_Vault/
│   ├── gmail_watcher.py     # Gmail monitoring + reply
│   ├── linkedin_watcher.py  # LinkedIn content generation
│   ├── approval_workflow.py # HITL approval system
│   ├── scheduler.py         # Task scheduling
│   ├── plan_generator.py    # Plan.md generation
│   ├── filesystem_watcher.py # Bronze tier file monitoring
│   ├── Config/
│   │   ├── gmail_config.json      # Gmail settings
│   │   └── linkedin_config.json   # LinkedIn settings
│   ├── Needs_Action/        # Tasks requiring action
│   ├── Pending_Approval/    # Awaiting human approval
│   ├── Approved/            # Approved for execution
│   ├── Rejected/            # Rejected actions
│   ├── Done/                # Completed tasks
│   ├── Plans/               # Generated plans
│   └── Logs/                # Activity logs
├── mcp_servers/
│   ├── email_mcp.py         # Email sending MCP
│   └── email_mcp.json       # MCP config
└── .claude/skills/
    ├── silver-tier.py       # Combined Silver Tier skill
    ├── approval-workflow.py # Approval workflow skill
    └── ...                  # Other skills
```

---

## Security Notes

1. **Never commit credentials.json or token.pickle to git**
2. **Use App Passwords for SMTP, not your regular Gmail password**
3. **Keep your OAuth tokens secure (token.pickle)**
4. **Review all actions in Pending_Approval before approving**

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Setup Gmail API credentials
3. ✅ Configure SMTP
4. ✅ Test Gmail watcher
5. ✅ Test LinkedIn content generation
6. ✅ Setup scheduler
7. ⬜ Review and approve queued items
8. ⬜ Monitor logs in `AI_Employee_Vault/Logs/`
9. ⬜ Customize templates in Config files
10. ⬜ Consider Gold Tier: Odoo integration, more platforms
