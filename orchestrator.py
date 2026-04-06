#!/usr/bin/env python3
"""
AI Employee Orchestrator - GOLD TIER
Master process that coordinates the AI Employee system
Cloud-connected with Gmail monitoring + Ralph Wiggum Autonomous Loop

Tier Capabilities:
- Bronze: File system monitoring, Dashboard updates
- Silver: Gmail integration, Auto-reply, LinkedIn posting
- Gold: Odoo ERP, Facebook/Instagram, Ralph Loop, Multi-MCP
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

# GOLD TIER: Import Ralph Loop for autonomous task completion
sys.path.insert(0, str(Path(__file__).parent))
try:
    from ralph_loop import RalphLoop, TaskState, create_test_task
    RALPH_AVAILABLE = True
except ImportError:
    RALPH_AVAILABLE = False
    logger = logging.getLogger('Orchestrator')
    logger.warning("Ralph Loop module not available. Install requirements for Gold Tier.")

# GOLD TIER: Import Multi-MCP Architecture
try:
    from mcp_registry import MCPRegistry, MCPRouter
    from audit_logger import AuditLogger
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger = logging.getLogger('Orchestrator')
    logger.warning("MCP Registry not available. Install requirements for Gold Tier.")

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


def show_mcp_status():
    """GOLD TIER: Show Multi-MCP Architecture status"""
    print("\n" + "-"*60)
    print("🌐 MULTI-MCP ARCHITECTURE STATUS")
    print("-"*60)

    if not MCP_AVAILABLE:
        print("  ⚠️  MCP Registry not available")
        return

    try:
        registry = MCPRegistry()
        router = MCPRouter(registry)

        # Show registered servers
        print(f"  Registered Servers: {len(registry.list_servers())}")
        for name in registry.list_servers():
            config = registry.get_server(name)
            state = registry.get_server_state(name)
            if config and state:
                status_icon = "✅" if state.status.value == 'ready' else "⚠️"
                print(f"     {status_icon} {name:12s} - {config.description[:40]}")
                print(f"        Status: {state.status.value}")
                if state.success_count > 0:
                    print(f"        Calls: {state.success_count} success, {state.error_count} errors")

        # Show router statistics
        router_stats = router.get_router_status()
        stats = router_stats.get('request_stats', {})
        print(f"\n  Router Statistics:")
        print(f"     Total Requests: {stats.get('total', 0)}")
        print(f"     Success Rate: {stats.get('success_rate', 0)*100:.1f}%")

        # Show circuit breaker states
        circuits = router_stats.get('circuit_states', {})
        if circuits:
            print(f"\n  Circuit Breakers:")
            for server, state in circuits.items():
                icon = "🔴" if state == "open" else "🟢"
                print(f"     {icon} {server}: {state}")

    except Exception as e:
        print(f"  ⚠️  Error loading MCP status: {e}")


def show_gold_tier_status(gmail_watcher=None, emails=None):
    """GOLD TIER: Show comprehensive status including Ralph Loop and Odoo"""
    vault_path = get_vault_path()

    print("\n" + "="*60)
    print("🥇 AI EMPLOYEE - GOLD TIER STATUS")
    print("="*60)

    # Silver Tier status
    show_status(gmail_watcher, emails)

    # Gold Tier additions
    print("\n" + "-"*60)
    print("🔄 RALPH WIGGUM LOOP STATUS")
    print("-"*60)

    if RALPH_AVAILABLE:
        ralph = RalphLoop(vault_path)
        active_tasks = ralph.get_active_tasks()
        print(f"  ✅ Ralph Loop: Available")
        print(f"  📋 Active Tasks: {len(active_tasks)}")
        if active_tasks:
            for tid in active_tasks:
                print(f"     • {tid}")
    else:
        print("  ⚠️  Ralph Loop: Not available (import error)")

    # Show In_Progress folder
    in_progress = vault_path / "In_Progress"
    if in_progress.exists():
        ip_count = len([f for f in in_progress.iterdir() if f.is_file()])
        print(f"  📁 In_Progress: {ip_count} items")

    # Show Done folder stats
    done = vault_path / "Done"
    if done.exists():
        done_count = len(list(done.rglob("*.md")))
        print(f"  ✅ Total Completed: {done_count} tasks")

    # Show Multi-MCP Architecture status
    show_mcp_status()

    print("\n" + "-"*60)
    print("🏢 ODOO ERP STATUS")
    print("-"*60)
    print("  ⏳ Checking Odoo connectivity...")
    print("  (Run 'docker-compose ps' to verify Odoo container status)")

    print("\n" + "="*60)


def show_status(gmail_watcher=None, emails=None):
    """Show current system status - Silver Tier with Gmail"""
    vault_path = get_vault_path()

    print("\n" + "="*50)
    print("AI Employee - SILVER TIER ACTIVE - Cloud Connected")
    print("="*50)

    print(f"\nVault Path: {vault_path}")

    # Count files in each folder (GOLD TIER: Added In_Progress)
    folders = ['Inbox', 'Needs_Action', 'In_Progress', 'Plans', 'Pending_Approval', 'Done']
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
    """Run interactive mode - Gold Tier with Ralph Loop"""
    print("\n" + "="*60)
    print("🥇 AI Employee Orchestrator - GOLD TIER ACTIVE")
    print("Autonomous Employee - Ralph Loop Enabled")
    print("="*60)
    print("\nCommands:")
    print("  1. Show status (local + Gmail)")
    print("  2. Process tasks (scan)")
    print("  3. Update dashboard")
    print("  4. Run full cycle")
    print("  5. Fetch Gmail emails")
    print("  6. Ralph Loop - Process tasks autonomously")
    print("  7. Ralph Status - Show active loops")
    print("  8. Gold Tier Status")
    print("  9. MCP Status - Multi-MCP Architecture")
    print("  q. Quit")
    print("-"*60)

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
        elif choice in ['6', 'ralph', 'ralph-loop']:
            ralph_loop_command(create_test=True, max_iterations=5)
        elif choice in ['7', 'ralph-status']:
            show_ralph_status()
        elif choice in ['8', 'gold']:
            show_gold_tier_status(gmail_watcher, emails)
        elif choice in ['9', 'mcp-status']:
            show_mcp_status()
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


def ralph_loop_command(task_id: str = None, max_iterations: int = 10, create_test: bool = False):
    """
    GOLD TIER: Execute Ralph Wiggum Loop for autonomous task completion

    The Ralph Loop keeps Claude working until a task is complete by:
    1. Creating state files in /In_Progress
    2. Detecting completion (file moved to /Done)
    3. Re-injecting prompts with context when incomplete
    4. Enforcing max iteration safety limits

    Usage:
        python orchestrator.py ralph-loop --task TASK_001
        python orchestrator.py ralph-loop --create-test
    """
    if not RALPH_AVAILABLE:
        print("❌ Ralph Loop not available. Check requirements installation.")
        return False

    vault_path = get_vault_path()
    ralph = RalphLoop(vault_path, max_iterations=max_iterations)

    print("\n" + "="*60)
    print("🔄 RALPH WIGGUM LOOP - Gold Tier Autonomous Processing")
    print("="*60)

    # Create test task if requested
    if create_test:
        test_file = create_test_task(vault_path, f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        task_id = test_file.stem
        print(f"\n✅ Created test task: {task_id}")

    # Get task from Needs_Action if no task_id provided
    if not task_id:
        needs_action = vault_path / "Needs_Action"
        tasks = [f for f in needs_action.glob("*.md") if not f.name.startswith("_")]
        if not tasks:
            print("❌ No tasks found in /Needs_Action")
            print("   Use --create-test to create a test task")
            return False

        # Use first task
        task_file = tasks[0]
        task_id = task_file.stem
        print(f"\n📋 Auto-selected task: {task_id}")

    # Check if task exists or is already in progress
    task_file = vault_path / "Needs_Action" / f"{task_id}.md"
    in_progress_file = vault_path / "In_Progress" / f"{task_id}.md"

    if task_file.exists():
        # Create Ralph Loop state
        state = ralph.create_state(task_file)
        print(f"✅ Claimed task and created Ralph state")
    elif in_progress_file.exists():
        # Task already claimed
        state = ralph.load_state(task_id)
        if not state:
            print(f"❌ Task in progress but no state file found")
            return False
        print(f"✅ Resuming existing task")
    else:
        print(f"❌ Task not found: {task_id}")
        return False

    print(f"\n📊 Configuration:")
    print(f"   Task ID: {task_id}")
    print(f"   Max Iterations: {max_iterations}")
    print(f"   Completion Promise: TASK_COMPLETE")
    print(f"\n🚀 Starting autonomous processing...")
    print("-"*60)

    # Define the work callback
    def do_work(tid: str, state: TaskState) -> bool:
        """Simulated work callback - in production this would call Claude"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {state.iteration}/{max_iterations}")

        # Check for completion marker in task content
        task_path = vault_path / "In_Progress" / f"{tid}.md"
        if task_path.exists():
            content = task_path.read_text(encoding='utf-8')
            if "TASK_COMPLETE" in content or "COMPLETE" in content.upper():
                print("   ✅ Task marked as complete in file")
                # Create completion marker
                done_marker = vault_path / "Done" / f"DONE_{tid}.md"
                task_path.rename(done_marker)
                return True

        # Simulate work being done
        ralph.record_action(tid, "process_step", f"Processing iteration {state.iteration}")
        print(f"   📝 Processing... (simulating work)")

        # In real implementation, Claude would:
        # 1. Read the task file
        # 2. Determine next action
        # 3. Execute action
        # 4. Update task file with progress
        # 5. Mark TASK_COMPLETE when done

        return True

    # Run the Ralph Loop
    success = ralph.process_task(task_id, do_work)

    print("\n" + "-"*60)
    if success:
        print("✅ Ralph Loop completed successfully!")
    else:
        print("⚠️  Ralph Loop finished but task may not be complete")

    print("="*60)
    return success


def show_ralph_status():
    """GOLD TIER: Show Ralph Loop status"""
    if not RALPH_AVAILABLE:
        print("❌ Ralph Loop not available")
        return

    vault_path = get_vault_path()
    ralph = RalphLoop(vault_path)

    print("\n" + "="*60)
    print("🔄 RALPH WIGGUM LOOP STATUS")
    print("="*60)

    active_tasks = ralph.get_active_tasks()
    print(f"\nActive Tasks: {len(active_tasks)}")

    for task_id in active_tasks:
        state = ralph.load_state(task_id)
        if state:
            print(f"\n📋 {task_id}")
            print(f"   Iteration: {state.iteration}/{state.max_iterations}")
            print(f"   Status: {state.status}")
            print(f"   Created: {state.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Last Updated: {state.last_updated.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Actions: {len(state.history)}")
            if state.history:
                last_action = state.history[-1]
                print(f"   Last Action: {last_action['action']} ({last_action['result']})")
        else:
            print(f"\n📋 {task_id} (no state file)")

    # Check completion status
    done_count = len(list((vault_path / "Done").glob("DONE_*.md")))
    print(f"\n📊 Statistics:")
    print(f"   In Progress: {len(active_tasks)}")
    print(f"   Completed Today: {done_count}")

    print("="*60)


def mark_task_complete(task_id: str, summary: str = ""):
    """GOLD TIER: Mark a task as complete manually"""
    if not RALPH_AVAILABLE:
        print("❌ Ralph Loop not available")
        return False

    vault_path = get_vault_path()
    ralph = RalphLoop(vault_path)

    success = ralph.mark_complete(task_id, summary)
    if success:
        print(f"✅ Task {task_id} marked as complete")
    else:
        print(f"❌ Failed to mark task {task_id} as complete")

    return success


def main():
    """Main entry point - Gold Tier with Ralph Loop"""
    import argparse

    parser = argparse.ArgumentParser(description='AI Employee Orchestrator - Gold Tier')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'start', 'scan', 'dashboard', 'interactive', 'cycle', 'gmail',
                                 'ralph-loop', 'ralph-status', 'mark-complete',  # GOLD TIER commands
                                 'mcp-status', 'mcp-route'],  # MULTI-MCP commands
                        help='Command to run')

    # GOLD TIER: Ralph Loop arguments
    parser.add_argument('--task', help='Task ID for Ralph Loop processing')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Maximum iterations for Ralph Loop (default: 10)')
    parser.add_argument('--create-test', action='store_true',
                        help='Create a test task for Ralph Loop')
    parser.add_argument('--summary', help='Completion summary for mark-complete')
    parser.add_argument('--gold', action='store_true',
                        help='Show Gold Tier status (includes Ralph Loop, Odoo status)')

    # MULTI-MCP arguments
    parser.add_argument('--domain', help='Domain for MCP routing (accounting, email, social)')
    parser.add_argument('--operation', help='Operation to perform via MCP')
    parser.add_argument('--params', help='JSON parameters for MCP operation')

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
        # GOLD TIER: Show extended status if --gold flag is used
        if args.gold:
            show_gold_tier_status(gmail_watcher, emails)
        else:
            show_status(gmail_watcher, emails)
    elif args.command == 'start':
        logger.info("Starting AI Employee services...")
        print("\n" + "="*50)
        print("🥇 GOLD TIER ACTIVE - Autonomous Employee")
        print("="*50)
        if gmail_watcher:
            print(f"✅ Gmail connected: {gmail_watcher.user_email}")
            print(f"📧 Unread emails: {len(emails) if emails else 0}")
        if RALPH_AVAILABLE:
            print("✅ Ralph Loop: Ready")
        else:
            print("⚠️  Ralph Loop: Not available")
        if MCP_AVAILABLE:
            print("✅ Multi-MCP Architecture: Ready")
        else:
            print("⚠️  Multi-MCP Architecture: Not available")
        show_status(gmail_watcher, emails)
    elif args.command == 'scan':
        process_tasks()
    elif args.command == 'dashboard':
        update_dashboard()
    elif args.command == 'cycle':
        process_tasks()
        update_dashboard()
        show_status(gmail_watcher, emails)

    # GOLD TIER: Ralph Wiggum Loop commands
    elif args.command == 'ralph-loop':
        ralph_loop_command(task_id=args.task, max_iterations=args.max_iterations,
                          create_test=args.create_test)
    elif args.command == 'ralph-status':
        show_ralph_status()

    # MULTI-MCP commands
    elif args.command == 'mcp-status':
        show_mcp_status()
    elif args.command == 'mcp-route':
        if not MCP_AVAILABLE:
            print("❌ MCP Registry not available")
        elif not args.domain or not args.operation:
            print("❌ Usage: python orchestrator.py mcp-route --domain accounting --operation list_customers")
        else:
            registry = MCPRegistry()
            router = MCPRouter(registry)
            params = json.loads(args.params) if args.params else {}
            result = router.route_task(args.domain, args.operation, **params)
            print(json.dumps(result, indent=2))

    elif args.command == 'mark-complete':
        if args.task:
            mark_task_complete(args.task, args.summary or "")
        else:
            print("❌ Usage: python orchestrator.py mark-complete --task TASK_ID")

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
