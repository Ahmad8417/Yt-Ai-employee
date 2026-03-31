#!/usr/bin/env python3
"""
Scheduler for AI Employee - Silver Tier
Manages cron/Task Scheduler jobs for automated operations
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class Scheduler:
    """Manages scheduled tasks for AI Employee"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.config_file = self.vault_path / 'Config' / 'scheduler_config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load scheduler configuration"""
        default_config = {
            'jobs': [
                {
                    'name': 'gmail_check',
                    'description': 'Check Gmail for new important emails',
                    'command': 'python AI_Employee_Vault/gmail_watcher.py',
                    'schedule': '*/5 * * * *',
                    'enabled': False
                },
                {
                    'name': 'daily_briefing',
                    'description': 'Generate daily business briefing',
                    'command': 'python .claude/skills/process-vault.py update-dashboard',
                    'schedule': '0 8 * * *',
                    'enabled': False
                },
                {
                    'name': 'linkedin_post',
                    'description': 'Queue LinkedIn posts for the week',
                    'command': 'python AI_Employee_Vault/linkedin_watcher.py schedule --days 7',
                    'schedule': '0 9 * * 1',
                    'enabled': False
                },
                {
                    'name': 'process_approved',
                    'description': 'Process approved actions',
                    'command': 'python AI_Employee_Vault/approval_workflow.py check-approved --execute',
                    'schedule': '*/10 * * * *',
                    'enabled': True
                }
            ],
            'last_run': {}
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    default_config.update(saved_config)
            except:
                pass

        return default_config

    def save_config(self):
        """Save scheduler configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def list_jobs(self):
        """List all scheduled jobs"""
        print("\n" + "="*60)
        print("SCHEDULED JOBS")
        print("="*60)

        for job in self.config['jobs']:
            status = "[ENABLED]" if job['enabled'] else "[DISABLED]"
            print(f"\n{status} {job['name']}")
            print(f"  Description: {job['description']}")
            print(f"  Schedule: {job['schedule']}")
            print(f"  Command: {job['command']}")

            # Show last run
            last_run = self.config['last_run'].get(job['name'], 'Never')
            print(f"  Last Run: {last_run}")

    def enable_job(self, job_name: str):
        """Enable a job"""
        for job in self.config['jobs']:
            if job['name'] == job_name:
                job['enabled'] = True
                self.save_config()
                print(f"Job enabled: {job_name}")
                return True
        print(f"Job not found: {job_name}")
        return False

    def disable_job(self, job_name: str):
        """Disable a job"""
        for job in self.config['jobs']:
            if job['name'] == job_name:
                job['enabled'] = False
                self.save_config()
                print(f"Job disabled: {job_name}")
                return True
        print(f"Job not found: {job_name}")
        return False

    def run_job(self, job_name: str):
        """Run a job immediately"""
        import subprocess

        for job in self.config['jobs']:
            if job['name'] == job_name:
                print(f"\nRunning job: {job_name}")
                print(f"Command: {job['command']}")
                print("-"*60)

                try:
                    result = subprocess.run(
                        job['command'],
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=str(self.vault_path.parent)
                    )

                    print(result.stdout)
                    if result.stderr:
                        print("STDERR:", result.stderr)

                    # Update last run
                    self.config['last_run'][job_name] = datetime.now().isoformat()
                    self.save_config()

                    print(f"\nJob completed with return code: {result.returncode}")
                    return result.returncode == 0

                except Exception as e:
                    print(f"Error running job: {e}")
                    return False

        print(f"Job not found: {job_name}")
        return False

    def run_scheduler(self):
        """Run the scheduler daemon"""
        import time
        import schedule

        print("\n" + "="*60)
        print("AI EMPLOYEE SCHEDULER DAEMON")
        print("="*60)
        print(f"Vault: {self.vault_path}")
        print("Press Ctrl+C to stop\n")

        # Schedule all enabled jobs
        for job in self.config['jobs']:
            if job['enabled']:
                self._schedule_job(schedule, job)
                print(f"Scheduled: {job['name']} ({job['schedule']})")

        # Run pending jobs
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nScheduler stopped.")

    def _schedule_job(self, schedule, job: Dict):
        """Parse cron-like schedule and add to scheduler"""
        cron = job['schedule']
        parts = cron.split()

        if len(parts) != 5:
            print(f"Invalid schedule for {job['name']}: {cron}")
            return

        minute, hour, day, month, day_of_week = parts

        # Build schedule
        if minute.startswith('*/'):
            interval = int(minute[2:])
            schedule.every(interval).minutes.do(self._execute_job, job)
        elif minute == '*':
            schedule.every().minute.do(self._execute_job, job)
        elif hour == '*':
            schedule.every().hour.at(f":{minute.zfill(2)}").do(self._execute_job, job)
        elif day_of_week == '*':
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(self._execute_job, job)
        elif day_of_week == '1':
            schedule.every().monday.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(self._execute_job, job)
        else:
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(self._execute_job, job)

    def _execute_job(self, job: Dict):
        """Execute a job and log result"""
        import subprocess

        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing: {job['name']}")

        try:
            result = subprocess.run(
                job['command'],
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.vault_path.parent)
            )

            # Update last run
            self.config['last_run'][job['name']] = datetime.now().isoformat()
            self.save_config()

            if result.returncode == 0:
                print(f"  [OK] {job['name']} completed successfully")
            else:
                print(f"  [FAIL] {job['name']} failed with code {result.returncode}")

        except Exception as e:
            print(f"  [ERROR] {job['name']}: {e}")

    def generate_windows_task(self, job_name: str):
        """Generate Windows Task Scheduler command"""
        for job in self.config['jobs']:
            if job['name'] == job_name:
                cron = job['schedule']
                parts = cron.split()
                if len(parts) == 5:
                    minute, hour, day, month, day_of_week = parts

                    command = f'''
# Windows Task Scheduler Command for {job_name}
# Run as Administrator in PowerShell:

$Action = New-ScheduledTaskAction -Execute "python" -Argument "{job['command']}"
$Trigger = New-ScheduledTaskTrigger -Daily -At {hour.zfill(2)}:{minute.zfill(2)}
$Settings = New-ScheduledTaskSettingsSet
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings
Register-ScheduledTask -TaskName "AIEmployee_{job_name}" -InputObject $Task -Force

# To remove:
# Unregister-ScheduledTask -TaskName "AIEmployee_{job_name}" -Confirm:$false
                    '''.strip()

                    print(command)
                    return command

        print(f"Job not found: {job_name}")
        return None

    def generate_cron_job(self, job_name: str):
        """Generate cron job entry"""
        for job in self.config['jobs']:
            if job['name'] == job_name:
                cron = job['schedule']
                command = job['command']

                entry = f"""
# Cron job for {job_name}
# Add to crontab with: crontab -e

{cron} cd {self.vault_path.parent} && {command} >> {self.vault_path}/Logs/{job_name}.log 2>&1

# Current crontab:
# crontab -l
                """.strip()

                print(entry)
                return entry

        print(f"Job not found: {job_name}")
        return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Scheduler for AI Employee')
    parser.add_argument('--vault', default='./AI_Employee_Vault',
                        help='Path to Obsidian vault')
    parser.add_argument('action', choices=['list', 'enable', 'disable', 'run',
                                           'daemon', 'windows-task', 'cron'],
                        help='Action to perform')
    parser.add_argument('--job', help='Job name')

    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    scheduler = Scheduler(str(vault_path))

    if args.action == 'list':
        scheduler.list_jobs()
    elif args.action == 'enable':
        if not args.job:
            print("Error: --job required")
            sys.exit(1)
        scheduler.enable_job(args.job)
    elif args.action == 'disable':
        if not args.job:
            print("Error: --job required")
            sys.exit(1)
        scheduler.disable_job(args.job)
    elif args.action == 'run':
        if not args.job:
            print("Error: --job required")
            sys.exit(1)
        scheduler.run_job(args.job)
    elif args.action == 'daemon':
        scheduler.run_scheduler()
    elif args.action == 'windows-task':
        if not args.job:
            print("Error: --job required")
            sys.exit(1)
        scheduler.generate_windows_task(args.job)
    elif args.action == 'cron':
        if not args.job:
            print("Error: --job required")
            sys.exit(1)
        scheduler.generate_cron_job(args.job)


if __name__ == '__main__':
    main()
