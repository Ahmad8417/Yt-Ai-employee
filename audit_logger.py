#!/usr/bin/env python3
"""
Audit Logger - GOLD TIER
=======================
Comprehensive logging of all AI actions for compliance and debugging.
Every MCP call, task completion, and approval is recorded.

Log Format:
    {
        "timestamp": "ISO8601",
        "action_type": "mcp_call|task_complete|approval_request|...",
        "actor": "claude_code|ai_employee|human",
        "target": "what_was_affected",
        "parameters": {...},
        "result": "success|failure",
        "approval_status": "approved|rejected|pending",
        "metadata": {...}
    }

Usage:
    from audit_logger import AuditLogger

    logger = AuditLogger()
    logger.log_mcp_call(
        server="odoo",
        operation="create_invoice",
        parameters={"partner_id": 123},
        result={"status": "success"},
        approved_by="human"
    )
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class ActionType(Enum):
    """Types of actions that can be logged"""
    MCP_CALL = "mcp_call"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EMAIL_SENT = "email_sent"
    EMAIL_DRAFTED = "email_drafted"
    INVOICE_CREATED = "invoice_created"
    CUSTOMER_CREATED = "customer_created"
    SOCIAL_POST = "social_post"
    RALPH_LOOP_ITERATION = "ralph_loop_iteration"
    SYSTEM_EVENT = "system_event"


class Actor(Enum):
    """Actors performing actions"""
    AI_EMPLOYEE = "ai_employee"
    CLAUDE_CODE = "claude_code"
    HUMAN = "human"
    SYSTEM = "system"


@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    action_type: str
    actor: str
    target: str
    parameters: Dict[str, Any]
    result: str
    duration_ms: Optional[float] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "actor": self.actor,
            "target": self.target,
            "parameters": self.parameters,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata or {}
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)


class AuditLogger:
    """
    Comprehensive audit logging for the AI Employee

    Logs to:
    1. JSON Lines file (machine readable)
    2. Markdown report (human readable)
    3. Console (debugging)
    """

    def __init__(self, vault_path: Optional[Path] = None,
                 retention_days: int = 90):
        """
        Initialize audit logger

        Args:
            vault_path: Path to AI Employee Vault
            retention_days: Days to retain logs
        """
        self.vault_path = Path(vault_path or os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault'))
        self.logs_path = self.vault_path / "Logs"
        self.audit_file = self.logs_path / "audit.jsonl"
        self.report_file = self.logs_path / "audit_report.md"
        self.retention_days = retention_days

        # Ensure logs directory exists
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Setup Python logger
        self.logger = logging.getLogger('AuditLogger')

        # Stats
        self.session_start = datetime.now()
        self.session_events = 0

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        random = hashlib.md5(timestamp.encode()).hexdigest()[:6]
        return f"req_{timestamp}_{random}"

    def _write_entry(self, entry: AuditEntry):
        """Write entry to audit log"""
        try:
            # Append to JSONL file
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict(), default=str) + '\n')

            self.session_events += 1

        except Exception as e:
            self.logger.error(f"Failed to write audit entry: {e}")

    def log(self, action_type: ActionType, actor: Actor, target: str,
            parameters: Dict[str, Any], result: str,
            duration_ms: Optional[float] = None,
            approval_status: Optional[str] = None,
            approved_by: Optional[str] = None,
            request_id: Optional[str] = None,
            correlation_id: Optional[str] = None,
            metadata: Dict[str, Any] = None):
        """
        Log a generic action

        Args:
            action_type: Type of action
            actor: Who performed the action
            target: What was affected
            parameters: Action parameters
            result: Success/failure
            duration_ms: Execution time
            approval_status: Approval state
            approved_by: Who approved
            request_id: Request ID
            correlation_id: Correlation ID for grouping
            metadata: Additional metadata
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action_type=action_type.value,
            actor=actor.value,
            target=target,
            parameters=parameters,
            result=result,
            duration_ms=duration_ms,
            approval_status=approval_status,
            approved_by=approved_by,
            request_id=request_id or self._generate_request_id(),
            correlation_id=correlation_id,
            metadata=metadata
        )

        self._write_entry(entry)

    def log_mcp_call(self, server: str, operation: str,
                    parameters: Dict[str, Any],
                    result: Dict[str, Any],
                    duration_ms: Optional[float] = None,
                    approved_by: Optional[str] = None):
        """Log MCP server call"""
        self.log(
            action_type=ActionType.MCP_CALL,
            actor=Actor.AI_EMPLOYEE,
            target=f"{server}.{operation}",
            parameters=parameters,
            result="success" if 'error' not in result else "failure",
            duration_ms=duration_ms,
            approved_by=approved_by,
            metadata={
                "server": server,
                "operation": operation,
                "response": result
            }
        )

    def log_task_created(self, task_id: str, task_type: str,
                        source: str, priority: str = "medium"):
        """Log task creation"""
        self.log(
            action_type=ActionType.TASK_CREATED,
            actor=Actor.SYSTEM,
            target=task_id,
            parameters={"task_type": task_type, "source": source, "priority": priority},
            result="success"
        )

    def log_task_completed(self, task_id: str, duration_seconds: float,
                         ralph_iterations: Optional[int] = None):
        """Log task completion"""
        self.log(
            action_type=ActionType.TASK_COMPLETED,
            actor=Actor.AI_EMPLOYEE,
            target=task_id,
            parameters={"duration_seconds": duration_seconds},
            result="success",
            duration_ms=duration_seconds * 1000,
            metadata={"ralph_iterations": ralph_iterations}
        )

    def log_task_failed(self, task_id: str, error: str):
        """Log task failure"""
        self.log(
            action_type=ActionType.TASK_FAILED,
            actor=Actor.AI_EMPLOYEE,
            target=task_id,
            parameters={"error": error},
            result="failure"
        )

    def log_approval_requested(self, action_type: str, target: str,
                              reason: str, request_id: str):
        """Log approval request"""
        self.log(
            action_type=ActionType.APPROVAL_REQUESTED,
            actor=Actor.AI_EMPLOYEE,
            target=target,
            parameters={"action_type": action_type, "reason": reason},
            result="pending",
            approval_status="pending",
            request_id=request_id
        )

    def log_approval(self, request_id: str, approved: bool,
                    approver: str, reason: Optional[str] = None):
        """Log approval/rejection"""
        self.log(
            action_type=ActionType.APPROVED if approved else ActionType.REJECTED,
            actor=Actor.HUMAN,
            target=request_id,
            parameters={"reason": reason},
            result="approved" if approved else "rejected",
            approval_status="approved" if approved else "rejected",
            approved_by=approver
        )

    def log_invoice_created(self, customer_id: int, amount: float,
                           invoice_id: int, approved_by: Optional[str] = None):
        """Log invoice creation"""
        self.log(
            action_type=ActionType.INVOICE_CREATED,
            actor=Actor.AI_EMPLOYEE,
            target=f"invoice:{invoice_id}",
            parameters={"customer_id": customer_id, "amount": amount},
            result="success",
            approved_by=approved_by
        )

    def log_customer_created(self, name: str, customer_id: int,
                            approved_by: Optional[str] = None):
        """Log customer creation"""
        self.log(
            action_type=ActionType.CUSTOMER_CREATED,
            actor=Actor.AI_EMPLOYEE,
            target=f"customer:{customer_id}",
            parameters={"name": name},
            result="success",
            approved_by=approved_by
        )

    def log_email(self, action: str, recipient: str, subject: str,
                 approved_by: Optional[str] = None,
                 sent: bool = False):
        """Log email action"""
        action_type = ActionType.EMAIL_SENT if sent else ActionType.EMAIL_DRAFTED
        self.log(
            action_type=action_type,
            actor=Actor.AI_EMPLOYEE,
            target=recipient,
            parameters={"subject": subject, "action": action},
            result="success" if sent else "draft",
            approved_by=approved_by
        )

    def log_ralph_iteration(self, task_id: str, iteration: int,
                           action_taken: str):
        """Log Ralph Loop iteration"""
        self.log(
            action_type=ActionType.RALPH_LOOP_ITERATION,
            actor=Actor.AI_EMPLOYEE,
            target=task_id,
            parameters={"iteration": iteration, "action": action_taken},
            result="success"
        )

    def generate_report(self, days: int = 7) -> Path:
        """
        Generate human-readable audit report

        Args:
            days: Number of days to include

        Returns:
            Path to generated report
        """
        since = datetime.now() - timedelta(days=days)
        entries = []

        # Read audit log
        if self.audit_file.exists():
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if entry_time >= since:
                            entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Generate Markdown report
        report_lines = [
            "---",
            f"title: AI Employee Audit Report - {datetime.now().strftime('%Y-%m-%d')}",
            f"period: Last {days} days",
            "---",
            "",
            "# AI Employee Audit Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Period:** Last {days} days",
            f"**Total Events:** {len(entries)}",
            "",
            "## Summary",
            ""
        ]

        # Calculate statistics
        action_counts = {}
        actor_counts = {}
        result_counts = {}

        for entry in entries:
            action = entry.get('action_type', 'unknown')
            actor = entry.get('actor', 'unknown')
            result = entry.get('result', 'unknown')

            action_counts[action] = action_counts.get(action, 0) + 1
            actor_counts[actor] = actor_counts.get(actor, 0) + 1
            result_counts[result] = result_counts.get(result, 0) + 1

        report_lines.append("### Actions")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            report_lines.append(f"- {action}: {count}")

        report_lines.extend(["", "### Actors"])
        for actor, count in sorted(actor_counts.items(), key=lambda x: -x[1]):
            report_lines.append(f"- {actor}: {count}")

        report_lines.extend(["", "### Results"])
        for result, count in sorted(result_counts.items(), key=lambda x: -x[1]):
            report_lines.append(f"- {result}: {count}")

        # Recent events
        report_lines.extend([
            "",
            "## Recent Events",
            ""
        ])

        for entry in entries[-20:]:  # Last 20 events
            ts = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
            report_lines.append(f"### {ts} - {entry['action_type']}")
            report_lines.append(f"- **Actor:** {entry['actor']}")
            report_lines.append(f"- **Target:** {entry['target']}")
            report_lines.append(f"- **Result:** {entry['result']}")
            if entry.get('approved_by'):
                report_lines.append(f"- **Approved By:** {entry['approved_by']}")
            report_lines.append("")

        # Write report
        self.report_file.write_text('\n'.join(report_lines), encoding='utf-8')

        self.logger.info(f"Generated audit report: {self.report_file}")
        return self.report_file

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get audit statistics"""
        since = datetime.now() - timedelta(days=days)

        stats = {
            "total_events": 0,
            "action_counts": {},
            "result_counts": {},
            "avg_duration_ms": 0,
            "approval_count": 0
        }

        durations = []

        if self.audit_file.exists():
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if entry_time >= since:
                            stats["total_events"] += 1
                            action = entry.get('action_type', 'unknown')
                            stats["action_counts"][action] = stats["action_counts"].get(action, 0) + 1

                            result = entry.get('result', 'unknown')
                            stats["result_counts"][result] = stats["result_counts"].get(result, 0) + 1

                            if entry.get('duration_ms'):
                                durations.append(entry['duration_ms'])

                            if entry.get('approval_status'):
                                stats["approval_count"] += 1
                    except (json.JSONDecodeError, KeyError):
                        continue

        if durations:
            stats["avg_duration_ms"] = sum(durations) / len(durations)

        return stats


def main():
    """Demo audit logger"""
    print("="*60)
    print("AUDIT LOGGER - GOLD TIER")
    print("="*60)

    logger = AuditLogger()

    # Log sample events
    print("\nLogging sample events...")

    logger.log_task_created("TASK_001", "email_response", "gmail_watcher")
    logger.log_mcp_call(
        server="odoo",
        operation="list_customers",
        parameters={"limit": 10},
        result={"status": "success", "count": 5},
        duration_ms=250,
        approved_by="auto"
    )
    logger.log_approval_requested(
        action_type="create_invoice",
        target="customer:123",
        reason="Amount exceeds $500 threshold",
        request_id="REQ_001"
    )
    logger.log_approval("REQ_001", approved=True, approver="user@example.com")
    logger.log_task_completed("TASK_001", duration_seconds=45.5, ralph_iterations=3)

    print("✅ Logged sample events")

    # Generate stats
    stats = logger.get_stats()
    print(f"\n📊 Statistics:")
    print(f"   Total events: {stats['total_events']}")
    print(f"   Actions: {stats['action_counts']}")
    print(f"   Results: {stats['result_counts']}")
    print(f"   Avg duration: {stats['avg_duration_ms']:.2f}ms")

    # Generate report
    report_path = logger.generate_report(days=1)
    print(f"\n📄 Report generated: {report_path}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
