#!/usr/bin/env python3
"""
Silver Tier Complete Skill for AI Employee
Integrates Gmail Watcher and LinkedIn Watcher with approval workflows
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


def get_vault_path() -> Path:
    """Get the vault path"""
    vault = os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault')
    return Path(vault).resolve()


def gmail_check():
    """Run Gmail watcher to check for new emails"""
    print("\n" + "="*60)
    print("CHECKING GMAIL")
    print("="*60)

    import subprocess
    vault_path = get_vault_path()
    gmail_script = vault_path / 'gmail_watcher.py'

    if not gmail_script.exists():
        print("[FAIL] Gmail watcher not found")
        return False

    result = subprocess.run(
        [sys.executable, str(gmail_script)],
        capture_output=True,
        text=True,
        cwd=str(vault_path.parent)
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    if result.returncode == 0:
        print("\n[OK] Gmail check completed")
        return True
    else:
        print(f"\n[FAIL] Gmail check failed")
        return False


def linkedin_generate(category: str = None):
    """Generate LinkedIn post content"""
    print("\n" + "="*60)
    print("GENERATING LINKEDIN POST")
    print("="*60)

    import subprocess
    vault_path = get_vault_path()
    linkedin_script = vault_path / 'linkedin_watcher.py'

    cmd = [sys.executable, str(linkedin_script), 'generate']
    if category:
        cmd.extend(['--category', category])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(vault_path.parent)
    )

    print(result.stdout)
    return result.returncode == 0


def linkedin_queue(category: str = None):
    """Queue a LinkedIn post for approval"""
    print("\n" + "="*60)
    print("QUEUING LINKEDIN POST")
    print("="*60)

    import subprocess
    vault_path = get_vault_path()
    linkedin_script = vault_path / 'linkedin_watcher.py'

    cmd = [sys.executable, str(linkedin_script), 'queue']
    if category:
        cmd.extend(['--category', category])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(vault_path.parent)
    )

    print(result.stdout)
    return result.returncode == 0


def linkedin_schedule(days: int = 7):
    """Schedule LinkedIn posts for upcoming days"""
    print("\n" + "="*60)
    print(f"SCHEDULING LINKEDIN POSTS FOR {days} DAYS")
    print("="*60)

    import subprocess
    vault_path = get_vault_path()
    linkedin_script = vault_path / 'linkedin_watcher.py'

    cmd = [sys.executable, str(linkedin_script), 'schedule', '--days', str(days)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(vault_path.parent)
    )

    print(result.stdout)
    return result.returncode == 0


def process_approved():
    """Process approved items from Approved folder"""
    print("\n" + "="*60)
    print("PROCESSING APPROVED ITEMS")
    print("="*60)

    vault_path = get_vault_path()
    approved_folder = vault_path / 'Approved'

    if not approved_folder.exists():
        print("[INFO] No Approved folder found")
        return True

    approved_files = list(approved_folder.glob('*.md'))

    if not approved_files:
        print("[INFO] No approved items to process")
        return True

    print(f"Found {len(approved_files)} approved item(s):")

    for item in approved_files:
        print(f"\n  Processing: {item.name}")
        content = item.read_text(encoding='utf-8')

        # Determine action type from frontmatter
        action_type = 'unknown'
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                frontmatter = content[3:end].strip()
                for line in frontmatter.split('\n'):
                    if line.startswith('type:'):
                        action_type = line.split(':', 1)[1].strip()
                        break

        print(f"    Type: {action_type}")
        print(f"    Status: Ready to execute (requires manual action for now)")

        # Move to Done
        done_folder = vault_path / 'Done' / datetime.now().strftime('%Y-%m-%d')
        done_folder.mkdir(parents=True, exist_ok=True)

        target = done_folder / f"EXECUTED_{item.name}"
        import shutil
        shutil.move(str(item), str(target))

        print(f"    Moved to: {target}")

    return True


def silver_tier_status():
    """Show Silver Tier status"""
    print("\n" + "="*60)
    print("SILVER TIER STATUS")
    print("="*60)

    vault_path = get_vault_path()

    # Check files
    files = {
        'Gmail Watcher': vault_path / 'gmail_watcher.py',
        'LinkedIn Watcher': vault_path / 'linkedin_watcher.py',
        'Dashboard': vault_path / 'Dashboard.md',
        'Company Handbook': vault_path / 'Company_Handbook.md',
    }

    print("\nComponents:")
    for name, filepath in files.items():
        status = "[OK]" if filepath.exists() else "[MISSING]"
        print(f"  {status} {name}")

    # Check folders
    folders = ['Inbox', 'Needs_Action', 'Pending_Approval', 'Approved', 'Done']
    print("\nFolders:")
    for folder in folders:
        folder_path = vault_path / folder
        status = "[OK]" if folder_path.exists() else "[MISSING]"
        print(f"  {status} {folder}/")

    # Count items
    needs_action = vault_path / 'Needs_Action'
    pending = vault_path / 'Pending_Approval'
    approved = vault_path / 'Approved'

    print("\nQueue Status:")
    print(f"  Needs Action: {len(list(needs_action.glob('*.md')))} items")
    print(f"  Pending Approval: {len(list(pending.glob('*.md')))} items")
    print(f"  Approved: {len(list(approved.glob('*.md')))} items")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Silver Tier Complete Skill')
    parser.add_argument('action', choices=[
        'gmail-check', 'linkedin-generate', 'linkedin-queue',
        'linkedin-schedule', 'process-approved', 'status'
    ], help='Action to perform')
    parser.add_argument('--category', help='LinkedIn content category')
    parser.add_argument('--days', type=int, default=7, help='Days to schedule')

    args = parser.parse_args()

    if args.action == 'gmail-check':
        gmail_check()
    elif args.action == 'linkedin-generate':
        linkedin_generate(args.category)
    elif args.action == 'linkedin-queue':
        linkedin_queue(args.category)
    elif args.action == 'linkedin-schedule':
        linkedin_schedule(args.days)
    elif args.action == 'process-approved':
        process_approved()
    elif args.action == 'status':
        silver_tier_status()


if __name__ == '__main__':
    main()
