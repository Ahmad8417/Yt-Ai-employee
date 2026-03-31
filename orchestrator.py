#!/usr/bin/env python3
"""
AI Employee Orchestrator - Bronze Tier
Master process that coordinates the AI Employee system
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

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


def show_status():
    """Show current system status"""
    vault_path = get_vault_path()

    print("\n" + "="*50)
    print("AI Employee - Bronze Tier Status")
    print("="*50)

    print(f"\nVault Path: {vault_path}")

    # Count files in each folder
    folders = ['Inbox', 'Needs_Action', 'Done', 'Plans', 'Pending_Approval']
    print("\nFolder Status:")
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

    print("\n" + "="*50)


def interactive_mode():
    """Run interactive mode"""
    print("\n" + "="*50)
    print("AI Employee Orchestrator - Bronze Tier")
    print("="*50)
    print("\nCommands:")
    print("  1. Show status")
    print("  2. Process tasks (scan)")
    print("  3. Update dashboard")
    print("  4. Run full cycle")
    print("  q. Quit")
    print("-"*50)

    while True:
        choice = input("\nEnter command: ").strip().lower()

        if choice in ['q', 'quit', 'exit']:
            print("Goodbye!")
            break
        elif choice in ['1', 'status']:
            show_status()
        elif choice in ['2', 'scan']:
            process_tasks()
        elif choice in ['3', 'dashboard']:
            update_dashboard()
        elif choice in ['4', 'cycle']:
            process_tasks()
            update_dashboard()
            show_status()
        else:
            print("Unknown command. Try: 1, 2, 3, 4, or q")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='AI Employee Orchestrator')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'start', 'scan', 'dashboard', 'interactive', 'cycle'],
                        help='Command to run')

    args = parser.parse_args()

    if args.command == 'status':
        show_status()
    elif args.command == 'start':
        logger.info("Starting AI Employee services...")
        # In Bronze Tier, we just show status
        show_status()
    elif args.command == 'scan':
        process_tasks()
    elif args.command == 'dashboard':
        update_dashboard()
    elif args.command == 'cycle':
        process_tasks()
        update_dashboard()
        show_status()
    elif args.command == 'interactive':
        interactive_mode()


if __name__ == '__main__':
    main()
