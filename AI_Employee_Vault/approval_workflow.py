#!/usr/bin/env python3
"""
Approval Workflow - Human-in-the-Loop (HITL) for AI Employee - Silver Tier
Manages sensitive actions requiring human approval
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List


def get_vault_path() -> Path:
    """Get the vault path"""
    vault = os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault')
    return Path(vault).resolve()


def create_approval_request(action_type: str, details: Dict) -> Path:
    """Create an approval request file for a sensitive action"""
    vault_path = get_vault_path()
    pending_folder = vault_path / 'Pending_Approval'
    pending_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    request_id = f"{action_type.upper()}_{timestamp}"

    # Build approval request content
    content_lines = [
        "---",
        f"type: approval_request",
        f"action: {action_type}",
        f"request_id: {request_id}",
        f"created: {datetime.now().isoformat()}",
        f"expires: {(datetime.now() + timedelta(days=7)).isoformat()}",
        "status: pending",
        "---",
        "",
        f"# Approval Request: {action_type.replace('_', ' ').title()}",
        "",
        "## Action Details",
    ]

    # Add details
    for key, value in details.items():
        content_lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")

    # Add instructions
    content_lines.extend([
        "",
        "## Instructions",
        "",
        "### To Approve",
        "1. Review the details above",
        "2. Move this file to `/Approved` folder",
        "3. The action will be executed automatically",
        "",
        "### To Reject",
        "1. Move this file to `/Rejected` folder",
        "2. Optionally add notes below explaining why",
        "",
        "## Approval Notes",
        "_Add any notes here before approving/rejecting_",
        "",
        "---",
        "*This request expires in 7 days*",
    ])

    # Write file
    request_file = pending_folder / f"{request_id}.md"
    request_file.write_text('\n'.join(content_lines), encoding='utf-8')

    # Log
    log_action('approval_request_created', request_id, action_type)

    print(f"Approval request created: {request_file.name}")
    print(f"Request ID: {request_id}")
    print(f"\nAction: {action_type}")
    print("Details:")
    for key, value in details.items():
        print(f"  {key}: {value}")

    return request_file


def check_approved_items() -> List[Path]:
    """Check Approved folder for items ready to execute"""
    vault_path = get_vault_path()
    approved_folder = vault_path / 'Approved'

    if not approved_folder.exists():
        return []

    approved_items = []
    for item in approved_folder.glob('*.md'):
        if item.is_file():
            approved_items.append(item)

    return approved_items


def execute_approved_action(approved_file: Path) -> bool:
    """Execute an approved action"""
    print(f"\nExecuting approved action: {approved_file.name}")

    # Parse the file to understand what to execute
    content = approved_file.read_text(encoding='utf-8')

    # Extract action type
    action_type = 'unknown'
    for line in content.split('\n'):
        if line.startswith('action:'):
            action_type = line.split(':', 1)[1].strip()
            break

    # In a real implementation, this would:
    # - Call MCP servers for external actions
    # - Send emails
    # - Make payments
    # - Post on social media

    print(f"  Action Type: {action_type}")
    print(f"  Status: Ready to execute (integration required)")

    # Move to Done
    vault_path = get_vault_path()
    done_folder = vault_path / 'Done' / datetime.now().strftime('%Y-%m-%d')
    done_folder.mkdir(parents=True, exist_ok=True)

    target = done_folder / f"EXECUTED_{approved_file.name}"
    shutil.move(str(approved_file), str(target))

    log_action('action_executed', approved_file.stem, action_type)

    print(f"  Moved to: {target}")

    return True


def list_pending_approvals() -> List[Dict]:
    """List all pending approval requests"""
    vault_path = get_vault_path()
    pending_folder = vault_path / 'Pending_Approval'

    if not pending_folder.exists():
        return []

    pending = []
    for item in pending_folder.glob('*.md'):
        if item.is_file():
            content = item.read_text(encoding='utf-8')

            # Extract metadata
            metadata = {}
            if content.startswith('---'):
                end = content.find('---', 3)
                if end > 0:
                    frontmatter = content[3:end].strip()
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()

            pending.append({
                'filename': item.name,
                'request_id': metadata.get('request_id', 'unknown'),
                'action': metadata.get('action', 'unknown'),
                'created': metadata.get('created', 'unknown'),
                'expires': metadata.get('expires', 'unknown'),
                'path': str(item)
            })

    return pending


def approve_request(request_id: str, notes: str = ""):
    """Move a request from Pending_Approval to Approved"""
    vault_path = get_vault_path()
    pending_folder = vault_path / 'Pending_Approval'
    approved_folder = vault_path / 'Approved'
    approved_folder.mkdir(parents=True, exist_ok=True)

    # Find the request file
    request_file = None
    for item in pending_folder.glob(f"{request_id}*.md"):
        request_file = item
        break

    if not request_file:
        print(f"Request not found: {request_id}")
        return False

    # Read and update content
    content = request_file.read_text(encoding='utf-8')
    content = content.replace('status: pending', 'status: approved')

    # Add approval notes
    if notes:
        content += f"\n\n## Approval Notes\n{notes}\n"

    # Write to approved folder
    target = approved_folder / request_file.name
    target.write_text(content, encoding='utf-8')

    # Remove from pending
    request_file.unlink()

    log_action('request_approved', request_id, notes)
    print(f"Request approved: {request_id}")

    return True


def reject_request(request_id: str, notes: str = ""):
    """Move a request from Pending_Approval to Rejected"""
    vault_path = get_vault_path()
    pending_folder = vault_path / 'Pending_Approval'
    rejected_folder = vault_path / 'Rejected'
    rejected_folder.mkdir(parents=True, exist_ok=True)

    # Find the request file
    request_file = None
    for item in pending_folder.glob(f"{request_id}*.md"):
        request_file = item
        break

    if not request_file:
        print(f"Request not found: {request_id}")
        return False

    # Read and update content
    content = request_file.read_text(encoding='utf-8')
    content = content.replace('status: pending', 'status: rejected')

    # Add rejection notes
    if notes:
        content += f"\n\n## Rejection Notes\n{notes}\n"

    # Write to rejected folder
    target = rejected_folder / request_file.name
    target.write_text(content, encoding='utf-8')

    # Remove from pending
    request_file.unlink()

    log_action('request_rejected', request_id, notes)
    print(f"Request rejected: {request_id}")

    return True


def log_action(action_type: str, request_id: str, details: str):
    """Log actions"""
    vault_path = get_vault_path()
    log_dir = vault_path / 'Logs'
    log_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f'{today}.json'

    entry = {
        'timestamp': datetime.now().isoformat(),
        'action_type': action_type,
        'request_id': request_id,
        'details': details
    }

    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    else:
        logs = []

    logs.append(entry)

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Approval Workflow for AI Employee')
    parser.add_argument('action', choices=['create-request', 'check-approved',
                                             'list-pending', 'approve', 'reject'],
                        help='Action to perform')
    parser.add_argument('--action-type', help='Type of action (for create-request)')
    parser.add_argument('--details', help='Details as JSON (for create-request)')
    parser.add_argument('--request-id', help='Request ID (for approve/reject)')
    parser.add_argument('--notes', help='Notes for approval/rejection')
    parser.add_argument('--execute', action='store_true',
                        help='Execute approved items after checking')

    args = parser.parse_args()

    if args.action == 'create-request':
        if not args.action_type:
            print("Error: --action-type required for create-request")
            sys.exit(1)

        details = {}
        if args.details:
            try:
                details = json.loads(args.details)
            except:
                print("Error: --details must be valid JSON")
                sys.exit(1)

        create_approval_request(args.action_type, details)

    elif args.action == 'check-approved':
        approved = check_approved_items()
        print(f"\nFound {len(approved)} approved item(s):")
        for item in approved:
            print(f"  - {item.name}")

        if args.execute and approved:
            print("\nExecuting approved actions...")
            for item in approved:
                execute_approved_action(item)

    elif args.action == 'list-pending':
        pending = list_pending_approvals()
        print(f"\n{len(pending)} pending approval(s):")
        for p in pending:
            print(f"\n  Request: {p['request_id']}")
            print(f"  Action: {p['action']}")
            print(f"  Created: {p['created']}")
            print(f"  Expires: {p['expires']}")

    elif args.action == 'approve':
        if not args.request_id:
            print("Error: --request-id required for approve")
            sys.exit(1)
        approve_request(args.request_id, args.notes)

    elif args.action == 'reject':
        if not args.request_id:
            print("Error: --request-id required for reject")
            sys.exit(1)
        reject_request(args.request_id, args.notes)


if __name__ == '__main__':
    main()
