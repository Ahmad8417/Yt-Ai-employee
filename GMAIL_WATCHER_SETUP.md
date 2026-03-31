# Gmail Watcher Setup Guide

Complete guide for setting up the Gmail Watcher system with OAuth2 authentication.

## Quick Start

```bash
# 1. Install dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# 2. Set up Google Cloud credentials (see below)

# 3. Run the watcher
python AI_Employee_Vault/gmail_watcher.py
```

## Prerequisites

- Python 3.7+
- A Google account with Gmail
- Access to [Google Cloud Console](https://console.cloud.google.com/)

## Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top
3. Click "New Project"
4. Enter a name (e.g., "AI Employee Gmail")
5. Click "Create"

### Step 2: Enable Gmail API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click on "Gmail API" and then click "Enable"
4. Wait for the API to be enabled (this may take a minute)

### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select **"Desktop"** as the user type
3. Click "Create"
4. Fill in:
   - **App name**: "AI Employee Gmail Watcher"
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click "Save and Continue"

### Step 4: Add Scopes

1. Click "Add or Remove Scopes"
2. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` - Read emails
   - `https://www.googleapis.com/auth/gmail.modify` - Mark as read
3. Click "Update" then "Save and Continue"

### Step 5: Add Test Users

1. Under "Test users", click "Add users"
2. Enter your Gmail address
3. Click "Add"
4. Click "Save and Continue"

### Step 6: Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "AI Employee Watcher"
5. Click "Create"
6. Click "Download JSON"
7. **Move the downloaded file to your project root and rename it to `credentials.json`**

### Step 7: Run the Watcher

```bash
# Navigate to your project
cd /path/to/Yt-Ai-employee

# Run the watcher
python AI_Employee_Vault/gmail_watcher.py
```

**On first run:**
- A browser window will open
- Sign in with your Gmail account
- Click "Allow" to grant permissions
- The `token.json` file will be created automatically

## File Structure

```
Yt-Ai-employee/
├── credentials.json          # Your OAuth client credentials (KEEP SECURE)
├── token.json                # Generated after first auth (KEEP SECURE)
├── AI_Employee_Vault/
│   └── gmail_watcher.py      # Main watcher code
└── GMAIL_WATCHER_SETUP.md    # This file
```

## Security Notes

- **Never commit `credentials.json` or `token.json` to git**
- Add these files to your `.gitignore`:
  ```
  credentials.json
  token.json
  *.json
  ```
- `credentials.json` contains your OAuth client secrets
- `token.json` contains your personal access tokens
- Both files should be treated as sensitive data

## Usage Examples

### Basic Usage

```bash
# Check unread emails (default)
python AI_Employee_Vault/gmail_watcher.py

# Check 5 unread emails and mark them as read
python AI_Employee_Vault/gmail_watcher.py --max 5 --mark-read

# Check all emails from a specific sender
python AI_Employee_Vault/gmail_watcher.py --query "from:boss@company.com"

# Check emails with specific subject
python AI_Employee_Vault/gmail_watcher.py --query "subject:Meeting"

# Check emails from last 7 days
python AI_Employee_Vault/gmail_watcher.py --query "newer_than:7d"

# Use custom port for OAuth callback
python AI_Employee_Vault/gmail_watcher.py --port 8080
```

### Programmatic Usage

```python
from AI_Employee_Vault.gmail_watcher import GmailWatcher

# Initialize
watcher = GmailWatcher(
    credentials_path='./credentials.json',
    token_path='./token.json',
    port=8080
)

# Fetch unread emails
emails = watcher.fetch_unread_emails(max_results=5)

# Print each email
for email in emails:
    print(f"Subject: {email['subject']}")
    print(f"From: {email['sender']}")
    print(f"Body: {email['body'][:500]}")

# Mark specific email as read
watcher.mark_as_read(email['id'])
```

## Gmail Search Queries

You can use any Gmail search query with the `--query` flag:

| Query | Description |
|-------|-------------|
| `is:unread` | Unread messages |
| `is:important` | Important messages |
| `from:email@example.com` | From specific sender |
| `to:email@example.com` | To specific recipient |
| `subject:"Meeting"` | Subject contains "Meeting" |
| `has:attachment` | Has attachments |
| `newer_than:2d` | Received in last 2 days |
| `older_than:1y` | Older than 1 year |
| `label:work` | In "work" label |
| `in:spam` | In spam folder |

Combine queries: `is:unread from:boss@company.com newer_than:7d`

## Troubleshooting

### "Credentials file not found"
- Ensure `credentials.json` is in the project root
- Check the file was downloaded from Google Cloud Console
- Verify the filename is exactly `credentials.json`

### "Error 403: access_denied"
- Your email is not added as a test user
- Go to OAuth consent screen and add your email

### "This app isn't verified"
- This is normal for testing
- Click "Advanced" then "Go to [app name] (unsafe)"

### "Port already in use"
- Change the port: `--port 8081`
- Or kill the process using port 8080

### Token expired
- The watcher automatically refreshes tokens
- If refresh fails, delete `token.json` and re-authenticate

### ImportError: No module named 'google'
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## API Quotas

- Gmail API has a quota of 250 quota units per user per second
- Reading messages: 5 units per request
- Modifying messages: 5 units per request
- For most personal use, you won't hit these limits

## Next Steps

Once set up, you can integrate the Gmail Watcher with:
- Obsidian vault for task management
- AI processing for email categorization
- Automatic replies based on email content
- Scheduled checking using cron or Task Scheduler

## Support

For issues with the Gmail API itself:
- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)

For OAuth issues:
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
