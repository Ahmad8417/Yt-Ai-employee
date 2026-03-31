#!/usr/bin/env python3
"""
Process Vault - Agent Skill for AI Employee (Bronze Tier)
This skill allows Claude to process tasks in the AI Employee vault.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


def get_vault_path() -> Path:
    """Get the vault path from environment or default"""
    vault = os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault')
    return Path(vault).resolve()


def scan_needs_action(vault_path: Path) -> List[Dict]:
    """Scan the Needs_Action folder and return list of tasks"""
    needs_action = vault_path / 'Needs_Action'

    if not needs_action.exists():
        return []

    tasks = []
    for item in needs_action.iterdir():
        if item.is_file() and item.suffix == '.md':
            content = item.read_text(encoding='utf-8')

            # Parse frontmatter
            task_info = {
                'id': item.stem,
                'filename': item.name,
                'path': str(item),
                'content': content,
                'type': 'unknown',
                'priority': 'medium',
                'status': 'pending'
            }

            # Extract metadata from frontmatter
            if content.startswith('---'):
                try:
                    end = content.find('---', 3)
                    if end > 0:
                        frontmatter = content[3:end].strip()
                        for line in frontmatter.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                task_info[key.strip()] = value.strip()
                except:
                    pass

            tasks.append(task_info)

    return tasks


def move_to_done(vault_path: Path, task_id: str, notes: str = "") -> bool:
    """Move a task from Needs_Action to Done"""
    needs_action = vault_path / 'Needs_Action'
    done = vault_path / 'Done'

    done.mkdir(parents=True, exist_ok=True)

    # Find the task file
    task_file = None
    for item in needs_action.iterdir():
        if item.stem == task_id or item.name.startswith(task_id):
            task_file = item
            break

    if not task_file:
        print(f"Task not found: {task_id}")
        return False

    # Create Done folder structure by date
    today = datetime.now().strftime('%Y-%m-%d')
    done_date_folder = done / today
    done_date_folder.mkdir(parents=True, exist_ok=True)

    # Move the file
    target = done_date_folder / task_file.name

    # Append completion metadata
    content = task_file.read_text(encoding='utf-8')
    completion_note = f"""

---
COMPLETED: {datetime.now().isoformat()}
NOTES: {notes}
---
"""
    content += completion_note
    target.write_text(content, encoding='utf-8')

    # Remove original
    task_file.unlink()

    print(f"Task moved to Done: {task_file.name}")
    return True


def update_dashboard(vault_path: Path, dry_run: bool = False) -> bool:
    """Update the Dashboard with current status"""
    dashboard_path = vault_path / 'Dashboard.md'

    # Count items in each folder
    needs_action_count = len(list((vault_path / 'Needs_Action').glob('*')))
    pending_approval_count = len(list((vault_path / 'Pending_Approval').glob('*')))

    # Count today's completed tasks
    today = datetime.now().strftime('%Y-%m-%d')
    done_today = vault_path / 'Done' / today
    done_count = len(list(done_today.glob('*'))) if done_today.exists() else 0

    # Read recent logs
    log_file = vault_path / 'Logs' / f'{today}.json'
    recent_activity = []
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
                recent_activity = logs[-5:]  # Last 5 entries
        except:
            pass

    if dry_run:
        print("[DRY RUN] Would update Dashboard with:")
        print(f"  - Needs_Action: {needs_action_count}")
        print(f"  - Pending_Approval: {pending_approval_count}")
        print(f"  - Done Today: {done_count}")
        return True

    # Update dashboard content
    activity_rows = []
    for log in recent_activity:
        time_str = log.get('timestamp', 'unknown')[:16]
        action = log.get('action_type', 'unknown')
        activity_rows.append(f"| {time_str} | {action} | ✅ Complete |")

    if not activity_rows:
        activity_rows = ["| - | No recent activity | - |"]

    dashboard_content = f"""---
name: AI Employee Dashboard
description: Real-time overview of tasks, activities, and system status
last_updated: {datetime.now().isoformat()}
---

# AI Employee Dashboard

## System Status

| Component | Status | Last Check |
|-----------|--------|------------|
| File Watcher | 🟢 Active | {datetime.now().strftime('%Y-%m-%d %H:%M')} |
| Claude Code | 🟢 Ready | {datetime.now().strftime('%Y-%m-%d %H:%M')} |
| Vault Sync | 🟢 OK | {datetime.now().strftime('%Y-%m-%d %H:%M')} |

---

## Pending Tasks Summary

| Folder | Count | Priority |
|--------|-------|----------|
| Needs_Action | {needs_action_count} | - |
| Pending_Approval | {pending_approval_count} | - |
| Done Today | {done_count} | - |

---

## Recent Activity

| Time | Action | Status |
|------|--------|--------|
{chr(10).join(activity_rows)}

---

## Quick Actions

- [ ] Review Needs_Action folder
- [ ] Check Pending_Approval items
- [ ] View Done tasks
- [ ] Run weekly briefing

---

*Last updated by AI Employee v0.1 - Bronze Tier*
"""

    dashboard_path.write_text(dashboard_content, encoding='utf-8')
    print(f"Dashboard updated at {datetime.now().isoformat()}")
    return True


def create_plan(vault_path: Path, task_id: str, plan_content: str) -> bool:
    """Create a plan file for a task"""
    plans_folder = vault_path / 'Plans'
    plans_folder.mkdir(parents=True, exist_ok=True)

    plan_file = plans_folder / f"PLAN_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    content = f"""---
type: plan
parent_task: {task_id}
created: {datetime.now().isoformat()}
status: pending
---

# Plan for Task: {task_id}

{plan_content}

---

*Generated by AI Employee*
"""

    plan_file.write_text(content, encoding='utf-8')
    print(f"Plan created: {plan_file.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Process AI Employee Vault')
    parser.add_argument('action', choices=['scan', 'process', 'move-to-done', 'update-dashboard'],
                        help='Action to perform')
    parser.add_argument('--task-id', help='Specific task ID to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without changes')
    parser.add_argument('--notes', help='Completion notes for move-to-done')
    parser.add_argument('--plan', help='Plan content for process action')

    args = parser.parse_args()

    vault_path = get_vault_path()
    print(f"Vault Path: {vault_path}")
    print(f"Action: {args.action}")

    if args.action == 'scan':
        tasks = scan_needs_action(vault_path)
        print(f"\nFound {len(tasks)} task(s) in Needs_Action:")
        for task in tasks:
            print(f"\n  [FILE] {task['filename']}")
            print(f"     Type: {task.get('type', 'unknown')}")
            print(f"     Priority: {task.get('priority', 'medium')}")

        # Output JSON for programmatic use
        output = {
            'vault_path': str(vault_path),
            'task_count': len(tasks),
            'tasks': [{'id': t['id'], 'type': t.get('type', 'unknown'), 'filename': t['filename']} for t in tasks]
        }
        print(f"\nJSON_OUTPUT:{json.dumps(output)}")

    elif args.action == 'process':
        if not args.task_id:
            print("Error: --task-id required for process action")
            sys.exit(1)

        tasks = scan_needs_action(vault_path)
        task = next((t for t in tasks if t['id'] == args.task_id or t['filename'].startswith(args.task_id)), None)

        if not task:
            print(f"Task not found: {args.task_id}")
            sys.exit(1)

        print(f"Processing task: {task['filename']}")
        print(f"Type: {task.get('type', 'unknown')}")
        print(f"Content preview: {task['content'][:200]}...")

        if args.plan:
            create_plan(vault_path, args.task_id, args.plan)

    elif args.action == 'move-to-done':
        if not args.task_id:
            print("Error: --task-id required for move-to-done action")
            sys.exit(1)

        move_to_done(vault_path, args.task_id, args.notes or "Completed by AI Employee")

    elif args.action == 'update-dashboard':
        update_dashboard(vault_path, args.dry_run)


if __name__ == '__main__':
    main()
