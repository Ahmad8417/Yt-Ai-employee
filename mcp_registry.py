#!/usr/bin/env python3
"""
Multi-MCP Architecture - GOLD TIER
=====================================
Central registry and router for managing multiple MCP servers.
This is the "nervous system" of the AI Employee, coordinating all external actions.

Architecture:
    Task Arrives → MCP Router → Determine Domain → Route to Server → Execute
                                                      ↓ (fallback)
                                              Circuit Breaker / Queue

Supported Servers:
    - email: Gmail/SMTP operations
    - odoo: Accounting and ERP operations
    - social: Facebook/Instagram operations
    - browser: Web automation (future)

Usage:
    from mcp_registry import MCPRegistry, MCPRouter

    registry = MCPRegistry()
    router = MCPRouter(registry)

    # Route a task
    result = router.route_task("accounting", "create_invoice", partner_id=123)
"""

import os
import sys
import json
import time
import logging
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logger = logging.getLogger('MCPRegistry')


class MCPStatus(Enum):
    """Status of an MCP server"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    description: str
    entrypoint: str  # Python module or command to run
    cwd: str = "."
    env_vars: Dict[str, str] = field(default_factory=dict)
    health_check: Optional[str] = None
    fallback: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True
    priority: int = 100  # Lower = higher priority

    @classmethod
    def from_dict(cls, data: dict) -> 'MCPServerConfig':
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            entrypoint=data['entrypoint'],
            cwd=data.get('cwd', '.'),
            env_vars=data.get('env_vars', {}),
            health_check=data.get('health_check'),
            fallback=data.get('fallback'),
            timeout=data.get('timeout', 30),
            retry_count=data.get('retry_count', 3),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 100)
        )


@dataclass
class MCPServerState:
    """Runtime state of an MCP server"""
    name: str
    status: MCPStatus = MCPStatus.UNKNOWN
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    capabilities: List[str] = field(default_factory=list)


class MCPRegistry:
    """
    Registry for managing multiple MCP servers

    Responsibilities:
    - Load server configurations
    - Start/stop servers
    - Monitor health
    - Maintain server states
    """

    def __init__(self, config_path: str = "mcp_servers/mcp_config.json"):
        self.config_path = Path(config_path)
        self.configs: Dict[str, MCPServerConfig] = {}
        self.states: Dict[str, MCPServerState] = {}
        self.processes: Dict[str, subprocess.Popen] = {}

        self._load_config()
        logger.info(f"MCP Registry initialized with {len(self.configs)} servers")

    def _load_config(self):
        """Load MCP server configurations from JSON"""
        if not self.config_path.exists():
            logger.warning(f"MCP config not found at {self.config_path}")
            self._create_default_config()
            return

        try:
            data = json.loads(self.config_path.read_text(encoding='utf-8'))
            for name, config_data in data.items():
                self.configs[name] = MCPServerConfig.from_dict(config_data)
                self.states[name] = MCPServerState(name=name)
            logger.info(f"Loaded {len(self.configs)} MCP server configurations")
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default MCP configuration"""
        default_config = {
            "email": {
                "name": "email-mcp",
                "description": "Email operations via Gmail/SMTP",
                "entrypoint": "python mcp_servers/email_mcp.py",
                "cwd": ".",
                "health_check": None,
                "fallback": "email_queue_mode",
                "priority": 100
            },
            "odoo": {
                "name": "odoo-mcp",
                "description": "Odoo 19+ Accounting MCP",
                "entrypoint": "python mcp_servers/odoo_mcp.py",
                "cwd": ".",
                "health_check": None,
                "fallback": "accounting_offline_mode",
                "priority": 90
            },
            "social": {
                "name": "social-mcp",
                "description": "Facebook/Instagram Social MCP",
                "entrypoint": "python mcp_servers/social_mcp.py",
                "cwd": ".",
                "health_check": None,
                "fallback": "social_queue_mode",
                "priority": 110
            }
        }

        # Save default config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(default_config, indent=2))
        logger.info(f"Created default MCP config at {self.config_path}")

        # Load it
        for name, config_data in default_config.items():
            self.configs[name] = MCPServerConfig.from_dict(config_data)
            self.states[name] = MCPServerState(name=name)

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get MCP server configuration by name"""
        return self.configs.get(name)

    def get_server_state(self, name: str) -> Optional[MCPServerState]:
        """Get MCP server runtime state"""
        return self.states.get(name)

    def list_servers(self) -> List[str]:
        """List all registered server names"""
        return list(self.configs.keys())

    def list_active_servers(self) -> List[str]:
        """List servers that are ready to accept requests"""
        active = []
        for name, state in self.states.items():
            config = self.configs.get(name)
            if config and config.enabled and state.status in [MCPStatus.READY, MCPStatus.BUSY]:
                active.append(name)
        return active

    def start_server(self, name: str) -> bool:
        """Start an MCP server process"""
        config = self.get_server(name)
        if not config:
            logger.error(f"Unknown MCP server: {name}")
            return False

        if not config.enabled:
            logger.warning(f"MCP server {name} is disabled")
            return False

        # Check if already running
        if name in self.processes and self.processes[name].poll() is None:
            logger.info(f"MCP server {name} already running (PID: {self.processes[name].pid})")
            self.states[name].status = MCPStatus.READY
            return True

        try:
            logger.info(f"Starting MCP server: {name}")
            self.states[name].status = MCPStatus.INITIALIZING
            self.states[name].start_time = datetime.now()

            # Prepare environment
            env = os.environ.copy()
            env.update(config.env_vars)

            # Start process
            process = subprocess.Popen(
                config.entrypoint.split(),
                cwd=config.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.processes[name] = process
            self.states[name].pid = process.pid
            self.states[name].status = MCPStatus.READY

            logger.info(f"Started {name} (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            self.states[name].status = MCPStatus.ERROR
            self.states[name].error_count += 1
            return False

    def stop_server(self, name: str) -> bool:
        """Stop an MCP server process"""
        if name not in self.processes:
            logger.warning(f"MCP server {name} not running")
            return True

        try:
            process = self.processes[name]
            logger.info(f"Stopping MCP server {name} (PID: {process.pid})")

            # Graceful shutdown
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            del self.processes[name]
            self.states[name].status = MCPStatus.OFFLINE
            self.states[name].pid = None

            logger.info(f"Stopped {name}")
            return True

        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")
            return False

    def stop_all(self):
        """Stop all MCP servers"""
        logger.info("Stopping all MCP servers...")
        for name in list(self.processes.keys()):
            self.stop_server(name)

    def health_check(self, name: str) -> bool:
        """Check health of an MCP server"""
        state = self.get_server_state(name)
        if not state:
            return False

        # Check if process is alive
        if name in self.processes:
            process = self.processes[name]
            if process.poll() is not None:
                # Process died
                logger.error(f"MCP server {name} process died")
                state.status = MCPStatus.ERROR
                state.error_count += 1
                return False

        # TODO: Implement HTTP health checks if configured
        state.last_health_check = datetime.now()
        return state.status in [MCPStatus.READY, MCPStatus.BUSY]

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report of all servers"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_servers": len(self.configs),
            "active_servers": len(self.list_active_servers()),
            "servers": {}
        }

        for name, config in self.configs.items():
            state = self.states.get(name)
            report["servers"][name] = {
                "enabled": config.enabled,
                "status": state.status.value if state else "unknown",
                "pid": state.pid if state else None,
                "error_count": state.error_count if state else 0,
                "success_count": state.success_count if state else 0,
                "avg_response_time": state.avg_response_time if state else 0
            }

        return report


class CircuitBreaker:
    """
    Circuit breaker pattern for MCP servers
    Prevents cascading failures by temporarily disabling failing servers
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures: Dict[str, int] = {}
        self.last_failure: Dict[str, datetime] = {}
        self.states: Dict[str, str] = {}  # closed, open, half-open

    def record_success(self, server_name: str):
        """Record a successful call"""
        self.failures[server_name] = 0
        self.states[server_name] = "closed"

    def record_failure(self, server_name: str):
        """Record a failed call"""
        if server_name not in self.failures:
            self.failures[server_name] = 0

        self.failures[server_name] += 1
        self.last_failure[server_name] = datetime.now()

        if self.failures[server_name] >= self.failure_threshold:
            self.states[server_name] = "open"
            logger.warning(f"Circuit breaker OPENED for {server_name}")

    def is_open(self, server_name: str) -> bool:
        """Check if circuit is open (server temporarily disabled)"""
        if server_name not in self.states:
            return False

        if self.states[server_name] == "open":
            # Check if recovery timeout has passed
            last_fail = self.last_failure.get(server_name)
            if last_fail:
                elapsed = (datetime.now() - last_fail).total_seconds()
                if elapsed > self.recovery_timeout:
                    self.states[server_name] = "half-open"
                    logger.info(f"Circuit breaker HALF-OPEN for {server_name}")
                    return False
            return True

        return False

    def get_state(self, server_name: str) -> str:
        """Get circuit state for a server"""
        return self.states.get(server_name, "closed")


class MCPRouter:
    """
    Router for directing tasks to appropriate MCP servers

    The router:
    1. Determines which MCP server can handle a task
    2. Applies circuit breaker pattern for reliability
    3. Handles fallbacks when servers are unavailable
    4. Records audit logs for all actions
    """

    # Domain to MCP server mapping
    DOMAIN_MAP = {
        "email": ["email"],
        "gmail": ["email"],
        "accounting": ["odoo"],
        "invoice": ["odoo"],
        "customer": ["odoo"],
        "odoo": ["odoo"],
        "social": ["social"],
        "facebook": ["social"],
        "instagram": ["social"],
        "post": ["social"]
    }

    def __init__(self, registry: MCPRegistry, audit_logger=None):
        self.registry = registry
        self.audit_logger = audit_logger
        self.circuit_breaker = CircuitBreaker()
        self.request_history: List[Dict] = []

    def _determine_servers(self, domain: str) -> List[str]:
        """Determine which MCP servers to use for a domain"""
        domain_lower = domain.lower()

        # Direct match
        if domain_lower in self.DOMAIN_MAP:
            return self.DOMAIN_MAP[domain_lower]

        # Partial match
        for key, servers in self.DOMAIN_MAP.items():
            if key in domain_lower or domain_lower in key:
                return servers

        return []

    def _execute_with_fallback(self, server_name: str, operation: str,
                               **kwargs) -> Dict[str, Any]:
        """Execute operation with fallback handling"""
        config = self.registry.get_server(server_name)

        if not config:
            return {"error": f"Unknown MCP server: {server_name}"}

        # Check circuit breaker
        if self.circuit_breaker.is_open(server_name):
            if config.fallback:
                logger.info(f"Circuit open for {server_name}, using fallback: {config.fallback}")
                return {"status": "fallback", "mode": config.fallback}
            return {"error": f"Circuit breaker open for {server_name}"}

        # Execute based on server type
        try:
            if server_name == "odoo":
                return self._execute_odoo(operation, **kwargs)
            elif server_name == "email":
                return self._execute_email(operation, **kwargs)
            elif server_name == "social":
                return self._execute_social(operation, **kwargs)
            else:
                return {"error": f"Unknown operation type: {server_name}"}

        except Exception as e:
            self.circuit_breaker.record_failure(server_name)
            logger.error(f"MCP execution failed: {e}")
            return {"error": str(e), "server": server_name}

    def _execute_odoo(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute Odoo MCP operation"""
        try:
            # Import Odoo MCP
            from mcp_servers.odoo_mcp import OdooMCP

            mcp = OdooMCP()
            if not mcp.client:
                return {"error": "Odoo not connected"}

            # Route to appropriate method
            if operation == "list_customers":
                return mcp.list_customers(**kwargs)
            elif operation == "create_customer":
                return mcp.create_customer(**kwargs)
            elif operation == "create_invoice":
                return mcp.create_invoice(**kwargs)
            elif operation == "get_outstanding_invoices":
                return mcp.get_outstanding_invoices(**kwargs)
            elif operation == "get_account_summary":
                return mcp.get_account_summary(**kwargs)
            elif operation == "post_journal_entry":
                return mcp.post_journal_entry(**kwargs)
            else:
                return {"error": f"Unknown Odoo operation: {operation}"}

        except Exception as e:
            logger.error(f"Odoo operation failed: {e}")
            return {"error": str(e)}

    def _execute_email(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute Email MCP operation"""
        # Email operations are handled by the existing email_mcp.py
        # This would integrate with the email MCP server
        return {"status": "queued", "domain": "email", "operation": operation}

    def _execute_social(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute Social MCP operation via Facebook/Instagram Graph API"""
        try:
            # Import Social MCP
            from mcp_servers.social_mcp import SocialMCP

            mcp = SocialMCP()

            # Route to appropriate method
            if operation == "post_to_page" or operation == "post_to_facebook":
                return mcp.post_to_page(
                    message=kwargs.get('message', ''),
                    link=kwargs.get('link'),
                    image_url=kwargs.get('image_url'),
                    auto_approve=kwargs.get('auto_approve', False)
                )
            elif operation == "post_to_instagram":
                return mcp.post_to_instagram(
                    image_url=kwargs.get('image_url'),
                    caption=kwargs.get('caption', ''),
                    auto_approve=kwargs.get('auto_approve', False)
                )
            elif operation == "get_page_insights":
                return mcp.get_page_insights(
                    since=kwargs.get('since'),
                    until=kwargs.get('until')
                )
            elif operation == "get_ig_insights":
                return mcp.get_instagram_insights(
                    since=kwargs.get('since'),
                    until=kwargs.get('until')
                )
            elif operation == "generate_weekly_report":
                return mcp.generate_weekly_report()
            elif operation == "test":
                return mcp.api.test_connection()
            else:
                return {"error": f"Unknown Social operation: {operation}"}

        except Exception as e:
            logger.error(f"Social operation failed: {e}")
            return {"error": str(e)}

    def route_task(self, domain: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Route a task to the appropriate MCP server

        Args:
            domain: Domain of the task (accounting, email, social)
            operation: Operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Result dictionary with status and data
        """
        start_time = time.time()
        request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(domain + operation) % 10000}"

        logger.info(f"Routing task [{request_id}]: {domain}.{operation}")

        # Determine servers
        servers = self._determine_servers(domain)
        if not servers:
            return {"error": f"No MCP server found for domain: {domain}"}

        # Try each server in order
        result = None
        used_server = None

        for server_name in servers:
            state = self.registry.get_server_state(server_name)
            if state and state.status in [MCPStatus.READY, MCPStatus.BUSY]:
                result = self._execute_with_fallback(server_name, operation, **kwargs)
                used_server = server_name

                # Record success/failure
                if 'error' not in result:
                    self.circuit_breaker.record_success(server_name)
                    if state:
                        state.success_count += 1
                else:
                    self.circuit_breaker.record_failure(server_name)
                    if state:
                        state.error_count += 1

                break

        # Record in history
        response_time = time.time() - start_time
        self.request_history.append({
            "request_id": request_id,
            "domain": domain,
            "operation": operation,
            "server": used_server,
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time,
            "success": 'error' not in result if result else False
        })

        # Update average response time
        if used_server:
            state = self.registry.get_server_state(used_server)
            if state:
                if state.avg_response_time == 0:
                    state.avg_response_time = response_time
                else:
                    state.avg_response_time = (state.avg_response_time * 0.9) + (response_time * 0.1)

        if result is None:
            return {"error": "No available MCP servers for domain", "domain": domain}

        return result

    def get_router_status(self) -> Dict[str, Any]:
        """Get router status and statistics"""
        total_requests = len(self.request_history)
        successful_requests = sum(1 for r in self.request_history if r['success'])

        return {
            "timestamp": datetime.now().isoformat(),
            "circuit_states": {
                name: self.circuit_breaker.get_state(name)
                for name in self.registry.list_servers()
            },
            "request_stats": {
                "total": total_requests,
                "successful": successful_requests,
                "failed": total_requests - successful_requests,
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0
            },
            "recent_requests": self.request_history[-10:]
        }


def main():
    """Demo the Multi-MCP Architecture"""
    print("="*60)
    print("MULTI-MCP ARCHITECTURE - GOLD TIER")
    print("="*60)

    # Initialize registry
    registry = MCPRegistry()
    print(f"\nLoaded {len(registry.list_servers())} MCP servers:")
    for name in registry.list_servers():
        config = registry.get_server(name)
        print(f"  - {name}: {config.description}")

    # Initialize router
    router = MCPRouter(registry)
    print("\nMCP Router initialized")

    # Show status
    print("\n" + "-"*60)
    print("MCP Status Report:")
    print("-"*60)
    report = registry.get_status_report()
    for name, status in report['servers'].items():
        status_icon = "ON" if status['status'] == 'ready' else "OFF"
        print(f"  [{status_icon}] {name:12s} - {status['status']}")

    print("\n" + "="*60)
    print("Multi-MCP Architecture ready for task routing!")
    print("="*60)


if __name__ == "__main__":
    main()
