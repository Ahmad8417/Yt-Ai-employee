#!/usr/bin/env python3
"""
AI Employee Orchestrator - Silver Tier
Master process that coordinates the AI Employee system
Cloud-connected with Gmail monitoring
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Import Gmail Watcher for Silver Tier
sys.path.insert(0, str(Path(__file__).parent / 'AI_Employee_Vault'))
from gmail_watcher import GmailWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_employee.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Orchestrator')


def get_vault_path() -> Path:
    """Get the vault path"""
    vault = os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault')
    return Path(vault).resolve()


def start_watcher() -> subprocess.Popen:
    """Start the filesystem watcher"""
    vault_path = get_vault_path()
    watcher_script = vault_path / 'filesystem_watcher.py'

    if not watcher_script.exists():
        logger.error(f"Watcher script not found: {watcher_script}")
        return None

    logger.info("Starting filesystem watcher...")
    process = subprocess.Popen(
        [sys.executable, str(watcher_script)],
        cwd=str(vault_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process


def process_tasks():
    """Process tasks in the Needs_Action folder"""
    vault_path = get_vault_path()
    skill_script = Path(__file__).parent / '.claude' / 'skills' / 'process-vault.py'

    if not skill_script.exists():
        # Try alternative path
        skill_script = Path('.claude/skills/process-vault.py')

    if not skill_script.exists():
        logger.warning(f"Skill script not found: {skill_script}")
        return

    try:
        result = subprocess.run(
            [sys.executable, str(skill_script), 'scan'],
            capture_output=True,
            text=True,
            cwd=str(vault_path.parent)
        )

        if result.returncode == 0:
            # Parse JSON output if present
            for line in result.stdout.split('\n'):
                if line.startswith('JSON_OUTPUT:'):
                    try:
                        data = json.loads(line.replace('JSON_OUTPUT:', ''))
                        logger.info(f"Found {data.get('task_count', 0)} tasks in Needs_Action")
                    except:
                        pass
        else:
            logger.error(f"Task scan failed: {result.stderr}")

    except Exception as e:
        logger.error(f"Error processing tasks: {e}")


def update_dashboard():
    """Update the dashboard"""
    vault_path = get_vault_path()
    skill_script = Path('.claude/skills/process-vault.py')

    try:
        result = subprocess.run(
            [sys.executable, str(skill_script), 'update-dashboard'],
            capture_output=True,
            text=True,
            cwd=str(vault_path.parent)
        )

        if result.returncode == 0:
            logger.info("Dashboard updated")
        else:
            logger.error(f"Dashboard update failed: {result.stderr}")

    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")


def show_status(gmail_watcher=None, emails=None):
    """Show current system status - Silver Tier with Gmail"""
    vault_path = get_vault_path()

    print("\n" + "="*50)
    print("AI Employee - SILVER TIER ACTIVE - Cloud Connected")
    print("="*50)

    print(f"\nVault Path: {vault_path}")

    # Count files in each folder
    folders = ['Inbox', 'Needs_Action', 'Done', 'Plans', 'Pending_Approval']
    print("\nLocal Vault Status:")
    for folder in folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            if folder == 'Done':
                # Count recursively for Done folder
                count = sum(1 for _ in folder_path.rglob('*') if _.is_file())
            else:
                count = len([f for f in folder_path.iterdir() if f.is_file()])
            print(f"  📁 {folder:20s}: {count:3d} items")
        else:
            print(f"  📁 {folder:20s}: Not created")

    # Check dashboard
    dashboard = vault_path / 'Dashboard.md'
    if dashboard.exists():
        print(f"\n  ✅ Dashboard.md exists")
    else:
        print(f"\n  ❌ Dashboard.md missing")

    # Check handbook
    handbook = vault_path / 'Company_Handbook.md'
    if handbook.exists():
        print(f"  ✅ Company_Handbook.md exists")
    else:
        print(f"  ❌ Company_Handbook.md missing")

    # Silver Tier: Show Gmail status
    print("\n" + "-"*50)
    print("Gmail Cloud Status:")
    print("-"*50)

    if gmail_watcher and gmail_watcher.service:
        print(f"  ✅ Connected: {gmail_watcher.user_email}")

        if emails is not None:
            print(f"  📧 Unread Emails: {len(emails)}")

            if emails:
                print("\n  Recent Unread Messages:")
                for i, email in enumerate(emails[:5], 1):  # Show top 5
                    subject = email.get('subject', 'No Subject')[:40]
                    sender = email.get('sender', 'Unknown')[:30]
                    print(f"    {i}. {subject}")
                    print(f"       From: {sender}")

                    # Check for special emails like 'Hackathon'
                    if 'hackathon' in subject.lower():
                        # Send auto-reply and mark as read
                        reply_message = "AI Agent: Silver Tier Demo Received! Your request is being processed by the AI Employee Vault."
                        if gmail_watcher.send_reply(email, reply_message):
                            gmail_watcher.mark_as_read(email['id'])
                            # Extract sender email
                            sender_full = email.get('sender', 'Unknown')
                            if '<' in sender_full and '>' in sender_full:
                                sender_email = sender_full[sender_full.find('<') + 1:sender_full.find('>')]
                            else:
                                sender_email = sender_full
                            print(f"       ✅ Reply Sent to {sender_email}")
                        else:
                            print(f"       ❌ Failed to send reply")
            else:
                print("  📭 No unread messages")
        else:
            print("  ⏳ Fetching emails...")
    else:
        print("  ❌ Gmail not connected")
        print("     Run with 'start' command to connect")

    print("\n" + "="*50)


def interactive_mode(gmail_watcher=None):
    """Run interactive mode - Silver Tier with Gmail"""
    print("\n" + "="*50)
    print("AI Employee Orchestrator - SILVER TIER ACTIVE")
    print("Cloud Connected - Gmail Integration Enabled")
    print("="*50)
    print("\nCommands:")
    print("  1. Show status (local + Gmail)")
    print("  2. Process tasks (scan)")
    print("  3. Update dashboard")
    print("  4. Run full cycle")
    print("  5. Fetch Gmail emails")
    print("  q. Quit")
    print("-"*50)

    emails = None

    while True:
        choice = input("\nEnter command: ").strip().lower()

        if choice in ['q', 'quit', 'exit']:
            print("Goodbye!")
            break
        elif choice in ['1', 'status']:
            show_status(gmail_watcher, emails)
        elif choice in ['2', 'scan']:
            process_tasks()
        elif choice in ['3', 'dashboard']:
            update_dashboard()
        elif choice in ['4', 'cycle']:
            process_tasks()
            update_dashboard()
            show_status(gmail_watcher, emails)
        elif choice in ['5', 'gmail', 'fetch']:
            if gmail_watcher:
                try:
                    print("\n📧 Fetching unread emails from Gmail...")
                    emails = gmail_watcher.fetch_unread_emails(max_results=10)
                    print(f"✅ Fetched {len(emails)} unread email(s)")
                    for i, email in enumerate(emails, 1):
                        subject = email.get('subject', 'No Subject')
                        print(f"  {i}. {subject}")
                        # Show processing for Hackathon emails
                        if 'hackathon' in subject.lower():
                            # Send auto-reply
                            reply_message = "AI Agent: Silver Tier Demo Received! Your request is being processed by the AI Employee Vault."
                            if gmail_watcher.send_reply(email, reply_message):
                                gmail_watcher.mark_as_read(email['id'])
                                print(f"     ✅ Reply Sent")
                            else:
                                print(f"     ❌ Failed to send reply")
                except Exception as e:
                    logger.error(f"Failed to fetch emails: {e}")
                    print(f"❌ Error: {e}")
            else:
                print("❌ Gmail watcher not initialized")
        else:
            print("Unknown command. Try: 1, 2, 3, 4, 5, or q")


def main():
    """Main entry point - Silver Tier with Gmail"""
    import argparse

    parser = argparse.ArgumentParser(description='AI Employee Orchestrator - Silver Tier')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'start', 'scan', 'dashboard', 'interactive', 'cycle', 'gmail'],
                        help='Command to run')

    args = parser.parse_args()

    # Initialize GmailWatcher for Silver Tier
    gmail_watcher = None
    emails = None

    if args.command in ['status', 'start', 'cycle', 'gmail']:
        try:
            # Use credentials.json and token.json from root directory
            root_path = Path(__file__).parent
            credentials_path = root_path / 'credentials.json'
            token_path = root_path / 'token.json'

            if credentials_path.exists():
                logger.info("Initializing Gmail Watcher...")
                gmail_watcher = GmailWatcher(
                    credentials_path=str(credentials_path),
                    token_path=str(token_path)
                )

                # Fetch unread emails on startup
                if args.command in ['start', 'cycle', 'gmail']:
                    logger.info("Fetching unread emails from Gmail...")
                    emails = gmail_watcher.fetch_unread_emails(max_results=10)
                    logger.info(f"Found {len(emails)} unread email(s)")

                    # Process Hackathon emails
                    for email in emails:
                        if 'hackathon' in email.get('subject', '').lower():
                            logger.info(f"Processing Hackathon email: {email['subject']}")
                            print(f"\n⏳ Processing Hackathon email: {email['subject']}")

                            # Extract sender email for display
                            sender = email.get('sender', 'Unknown')
                            if '<' in sender and '>' in sender:
                                sender_email = sender[sender.find('<') + 1:sender.find('>')]
                            else:
                                sender_email = sender

                            # Send auto-reply
                            reply_message = "AI Agent: Silver Tier Demo Received! Your request is being processed by the AI Employee Vault."
                            reply_sent = gmail_watcher.send_reply(email, reply_message)

                            if reply_sent:
                                # Mark email as read to prevent loop
                                gmail_watcher.mark_as_read(email['id'])
                                print(f"✅ Reply Sent to {sender_email}")
            else:
                logger.warning("credentials.json not found. Gmail features disabled.")
                print("\n⚠️  credentials.json not found in root directory.")
                print("    Gmail integration disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail Watcher: {e}")
            print(f"\n⚠️  Gmail connection failed: {e}")

    if args.command == 'status':
        show_status(gmail_watcher, emails)
    elif args.command == 'start':
        logger.info("Starting AI Employee services...")
        print("\n" + "="*50)
        print("SILVER TIER ACTIVE - Cloud Connected")
        print("="*50)
        if gmail_watcher:
            print(f"✅ Gmail connected: {gmail_watcher.user_email}")
            print(f"📧 Unread emails: {len(emails) if emails else 0}")
        show_status(gmail_watcher, emails)
    elif args.command == 'scan':
        process_tasks()
    elif args.command == 'dashboard':
        update_dashboard()
    elif args.command == 'cycle':
        process_tasks()
        update_dashboard()
        show_status(gmail_watcher, emails)
    elif args.command == 'gmail':
        # Just show Gmail status
        if gmail_watcher and emails is not None:
            print(f"\n{'='*50}")
            print(f"Gmail Status: {gmail_watcher.user_email}")
            print(f"{'='*50}")
            print(f"Unread emails: {len(emails)}\n")
            for i, email in enumerate(emails, 1):
                print(f"{i}. {email.get('subject', 'No Subject')}")
                print(f"   From: {email.get('sender', 'Unknown')}")
                if 'hackathon' in email.get('subject', '').lower():
                    # Send auto-reply
                    reply_message = "AI Agent: Silver Tier Demo Received! Your request is being processed by the AI Employee Vault."
                    if gmail_watcher.send_reply(email, reply_message):
                        gmail_watcher.mark_as_read(email['id'])
                        print(f"   ✅ Reply Sent")
                    else:
                        print(f"   ❌ Failed to send reply")
                print()
        else:
            print("❌ Gmail not connected")
    elif args.command == 'interactive':
        interactive_mode(gmail_watcher)


if __name__ == '__main__':
    main()
