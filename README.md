# Silver-Tier-AI-Agent

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Gmail API](https://img.shields.io/badge/Gmail%20API-v1-red)](https://developers.google.com/gmail/api)

> An autonomous AI Employee system that monitors Gmail, auto-responds to emails, and manages tasks through a local file-based vault.

## Project Demo

Click the thumbnail below to watch the full project demonstration:

[![Silver Tier AI Agent Demo](https://img.youtube.com/vi/VmvhC6jrhsk/0.jpg)](https://youtu.be/VmvhC6jrhsk)

**Video Link:** [https://youtu.be/VmvhC6jrhsk](https://youtu.be/VmvhC6jrhsk)

---

## Features

### Core Capabilities

- **Gmail Integration**: Real-time monitoring of unread emails via Gmail API
- **Auto-Reply System**: Automatically responds to specific email triggers (e.g., "Hackathon")
- **File-Based Vault**: Organizes tasks in folders (Inbox, Needs_Action, In_Progress, Done)
- **Dashboard**: Live Markdown dashboard showing system status
- **Task Processing**: Scans and processes tasks from the Needs_Action folder

### Silver Tier Features

| Feature | Description |
|---------|-------------|
| Gmail Watcher | OAuth2-based Gmail monitoring with token persistence |
| Auto-Response | Sends custom replies based on email subject keywords |
| Email Marking | Automatically marks processed emails as read |
| Task Automation | Processes tasks and updates dashboard automatically |
| File Monitoring | Watches vault folder for new files and changes |

---

## Project Structure

```
Silver-Tier-AI-Agent/
├── AI_Employee_Vault/          # Main vault folder
│   ├── Inbox/                  # New emails/files arrive here
│   ├── Needs_Action/           # Tasks requiring processing
│   ├── In_Progress/            # Tasks currently being worked on
│   ├── Plans/                  # Generated plans
│   ├── Pending_Approval/       # Tasks awaiting approval
│   ├── Done/                   # Completed tasks
│   ├── Logs/                   # System logs
│   ├── Config/                 # Configuration files
│   ├── gmail_watcher.py        # Gmail monitoring module
│   ├── filesystem_watcher.py   # File system monitoring
│   ├── Dashboard.md            # Live system dashboard
│   └── Company_Handbook.md     # Company guidelines
├── orchestrator.py             # Main entry point
├── requirements.txt            # Python dependencies
├── credentials.json            # Gmail API credentials (create this)
├── token.json                  # OAuth token (auto-generated)
└── README.md                   # This file
```

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- A Gmail account
- Google Cloud Project with Gmail API enabled

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ahmad8417/Silver-Tier-AI-Agent.git
   cd Silver-Tier-AI-Agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Gmail API credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the **Gmail API**
   - Create **OAuth 2.0 credentials** (Desktop app)
   - Download `credentials.json` and place it in the project root

4. **Run the orchestrator:**
   ```bash
   python orchestrator.py start
   ```

   On first run, a browser window will open for OAuth authentication.

---

## Usage

### Interactive Mode

```bash
python orchestrator.py interactive
```

Commands available:
- `1` or `status` - Show system status (local + Gmail)
- `2` or `scan` - Scan for new tasks
- `3` or `dashboard` - Update the dashboard
- `4` or `cycle` - Run full cycle (scan + dashboard + status)
- `5` or `gmail` - Fetch Gmail emails
- `q` or `quit` - Exit

### Auto-Reply Demo

Send an email with "Hackathon" in the subject to your connected Gmail account. The AI will:
1. Detect the keyword
2. Send an auto-reply
3. Mark the email as read

### Running Tests

```bash
python test_silver_tier.py
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_EMPLOYEE_VAULT` | Path to vault folder | `./AI_Employee_Vault` |

---

## Tech Stack

- **Python 3.8+** - Core language
- **Gmail API** - Email integration
- **Google OAuth2** - Authentication
- **watchdog** - File system monitoring
- **schedule** - Task scheduling

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Gmail API     │────▶│  Gmail Watcher   │────▶│  Orchestrator   │
│  (Cloud)        │     │  (OAuth2)        │     │  (Controller)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                         │
                            ┌──────────────────────────┼──────────────────────────┐
                            │                          │                          │
                            ▼                          ▼                          ▼
                   ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
                   │  File Watcher   │       │  Task Scanner   │       │   Dashboard     │
                   │  (Local Vault)  │       │  (Needs_Action) │       │   (Markdown)    │
                   └─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with Claude AI assistance
- Inspired by autonomous agent architectures
- Gmail API by Google Cloud Platform

---

## Author

**Ahmad** - [@Ahmad8417](https://github.com/Ahmad8417)

Project Link: [https://github.com/Ahmad8417/Silver-Tier-AI-Agent](https://github.com/Ahmad8417/Silver-Tier-AI-Agent)
