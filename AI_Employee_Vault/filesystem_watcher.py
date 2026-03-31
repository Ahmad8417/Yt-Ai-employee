#!/usr/bin/env python3
"""
Filesystem Watcher for AI Employee - Bronze Tier
Monitors the Inbox folder and moves files to Needs_Action
"""

import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FilesystemWatcher')


class VaultHandler(FileSystemEventHandler):
    """Handles file system events in the Inbox folder"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / 'Inbox'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.processed_ids = set()

        # Ensure directories exist
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

        logger.info(f"Watcher initialized for vault: {vault_path}")

    def on_created(self, event):
        """Called when a new file is created in the Inbox"""
        if event.is_directory:
            return

        source = Path(event.src_path)

        # Skip temporary files and our own metadata files
        if source.name.startswith('.') or source.name.endswith('.meta.json'):
            return

        logger.info(f"New file detected: {source.name}")

        # Wait a moment to ensure file is fully written
        time.sleep(0.5)

        try:
            self.process_file(source)
        except Exception as e:
            logger.error(f"Error processing file {source.name}: {e}")

    def process_file(self, source: Path):
        """Process a file from Inbox to Needs_Action"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_name = f"FILE_{timestamp}_{source.name}"
        target = self.needs_action / target_name

        # Move the file
        import shutil
        shutil.move(str(source), str(target))

        # Create metadata file
        self.create_metadata(source, target, timestamp)

        # Log the action
        self.log_action(source.name, target_name)

        logger.info(f"File moved to Needs_Action: {target_name}")

    def create_metadata(self, source: Path, target: Path, timestamp: str):
        """Create a markdown file with metadata"""
        meta_filename = f"FILE_{timestamp}_{source.name}.md"
        meta_path = self.needs_action / meta_filename

        # Get file stats
        try:
            stats = target.stat()
            size = stats.st_size
            created = datetime.fromtimestamp(stats.st_ctime).isoformat()
        except:
            size = 0
            created = datetime.now().isoformat()

        # Determine file type
        file_type = self.get_file_type(source.suffix)

        content = f"""---
type: file_drop
source: inbox
original_name: {source.name}
target_file: {target.name}
size: {size} bytes
received: {datetime.now().isoformat()}
file_type: {file_type}
status: pending
priority: medium
---

# File Drop: {source.name}

## Details
- **Original Name**: {source.name}
- **File Type**: {file_type}
- **Size**: {size} bytes
- **Received**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Suggested Actions
- [ ] Review file contents
- [ ] Determine appropriate action
- [ ] Process or archive

## Notes
_Add any notes here_
"""

        meta_path.write_text(content, encoding='utf-8')
        logger.info(f"Metadata created: {meta_filename}")

    def get_file_type(self, suffix: str) -> str:
        """Determine file type from extension"""
        types = {
            '.pdf': 'PDF Document',
            '.doc': 'Word Document',
            '.docx': 'Word Document',
            '.txt': 'Text File',
            '.md': 'Markdown',
            '.csv': 'CSV Spreadsheet',
            '.xlsx': 'Excel Spreadsheet',
            '.xls': 'Excel Spreadsheet',
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.png': 'Image',
        }
        return types.get(suffix.lower(), 'Unknown')

    def log_action(self, original_name: str, target_name: str):
        """Log the action to the daily log file"""
        log_dir = self.vault_path / 'Logs'
        log_dir.mkdir(exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': 'file_received',
            'original_name': original_name,
            'target_name': target_name,
            'watcher': 'filesystem'
        }

        # Append to existing log or create new
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
    # Get vault path from environment or use default
    vault_path = os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault')
    vault_path = Path(vault_path).resolve()

    logger.info(f"Starting Filesystem Watcher for: {vault_path}")
    logger.info("Bronze Tier - Personal AI Employee")

    # Create handler and observer
    event_handler = VaultHandler(str(vault_path))
    observer = Observer()
    observer.schedule(event_handler, str(vault_path / 'Inbox'), recursive=False)

    # Start watching
    observer.start()
    logger.info("Watcher started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped.")


if __name__ == '__main__':
    main()
