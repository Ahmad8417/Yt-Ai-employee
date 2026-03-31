# AI Employee - Bronze Tier
# Personal AI Employee Hackathon 2026

## Installation

1. Install Python 3.13 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Bronze Tier Requirements

✅ Obsidian vault with Dashboard.md and Company_Handbook.md
✅ One working Watcher script (filesystem monitoring)
✅ Claude Code successfully reading from and writing to the vault
✅ Basic folder structure: /Inbox, /Needs_Action, /Done
✅ Agent Skill for processing the vault

## Quick Start

1. **Start the watcher** (in one terminal):
   ```bash
   python AI_Employee_Vault/filesystem_watcher.py
   ```

2. **Drop a file into Inbox**:
   ```bash
   echo "Test content" > AI_Employee_Vault/Inbox/test_file.txt
   ```

3. **Check the Dashboard**:
   - Open `AI_Employee_Vault/Dashboard.md` in Obsidian

4. **Use the Orchestrator**:
   ```bash
   python orchestrator.py status
   python orchestrator.py scan
   python orchestrator.py dashboard
   ```

## Folder Structure

```
AI_Employee_Vault/
├── Inbox/              # Drop files here
├── Needs_Action/       # Tasks for AI to process
├── Done/               # Completed tasks (organized by date)
├── Plans/              # Generated plans
├── Pending_Approval/   # Waiting for human approval
├── Approved/           # Approved actions
├── Rejected/           # Rejected actions
├── Logs/               # Activity logs
├── Dashboard.md        # System overview
├── Company_Handbook.md # AI rules
└── filesystem_watcher.py # File monitoring script
```

## Agent Skills

The `process-vault` skill is available at `.claude/skills/process-vault.json`

## Testing

Run the test script:
```bash
python test_bronze_tier.py
```

This will:
1. Verify the folder structure
2. Drop test files into Inbox
3. Trigger the watcher
4. Process tasks
5. Update the dashboard
6. Move completed tasks to Done
