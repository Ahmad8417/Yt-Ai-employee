# Gold Tier Implementation Plan: Autonomous Employee

**Status:** Planning Complete | **Estimated Time:** 40+ hours | **Target:** Full Autonomous FTE

---

## Executive Summary

Gold Tier transforms the AI Employee from a reactive assistant (Silver) into an **Autonomous Employee** that:
- Runs business accounting via self-hosted Odoo ERP
- Manages social media presence (Facebook/Instagram)
- Completes multi-step tasks autonomously via Ralph Wiggum Loop
- Generates weekly CEO briefings with business insights
- Operates through a multi-MCP architecture for domain-specific actions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOCKER COMPOSE NETWORK                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │  AI Employee     │    │  Odoo Community  │    │  PostgreSQL      │     │
│  │  Core Container  │◄──►│  v19+ Container  │◄──►│  Database        │     │
│  │                  │    │                  │    │                  │     │
│  │  - Orchestrator  │    │  - Accounting    │    │  - Odoo Data     │     │
│  │  - Ralph Loop    │    │  - Invoicing     │    │  - Business Data │     │
│  │  - Watchers      │    │  - CRM           │    │                  │     │
│  └────────┬─────────┘    └──────────────────┘    └──────────────────┘     │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                     MULTI-MCP SERVERS                            │       │
│  ├─────────────────┬─────────────────┬─────────────────────────────┤       │
│  │ Accounting MCP  │ Social MCP      │ Email MCP (existing)        │       │
│  │ - Odoo JSON-RPC│ - Facebook Graph│ - SMTP/IMAP                 │       │
│  │ - Invoices     │ - Instagram     │ - Gmail API                 │       │
│  │ - Journal      │ - Analytics     │ - Send/receive              │       │
│  └─────────────────┴─────────────────┴─────────────────────────────┘       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    RALPH WIGGUM LOOP                             │       │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │       │
│  │  │ Task     │──►│ Process  │──►│ Check    │──►│ Complete?│     │       │
│  │  │ Created  │   │ Step     │   │ Progress │   │          │     │       │
│  │  └──────────┘   └──────────┘   └────┬─────┘   └────┬─────┘     │       │
│  │                                     │              │              │       │
│  │                              ┌────▼──────────────▼─────┐          │       │
│  │                              │  NO: Re-inject prompt   │          │       │
│  │                              │  with context          │          │       │
│  │                              └─────────────────────────┘          │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  AI Employee     │
                    │  Vault (Host FS) │
                    │                  │
                    │  - Inbox/        │
                    │  - Needs_Action/ │
                    │  - Done/         │
                    │  - Dashboard.md  │
                    └──────────────────┘
```

---

## Phase 1: Docker Compose + Odoo 19 Setup

### Step 1.1: Create docker-compose.yml

**Estimated:** 2-3 hours

```yaml
# docker-compose.yml structure
version: '3.8'

services:
  # PostgreSQL for Odoo
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - odoo-db-data:/var/lib/postgresql/data/pgdata
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Odoo Community v19+
  odoo:
    image: odoo:19.0  # or odoo:latest
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8069:8069"
      - "8072:8072"  # Longpolling
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
      - ODOO_RC=/etc/odoo/odoo.conf
    volumes:
      - odoo-data:/var/lib/odoo
      - ./odoo-config:/etc/odoo
      - ./odoo-addons:/mnt/extra-addons
    command: ["odoo", "--config", "/etc/odoo/odoo.conf"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8069/web/login"]
      interval: 30s
      timeout: 10s
      retries: 3

  # AI Employee Core
  ai-employee:
    build: .
    depends_on:
      - odoo
    environment:
      - AI_EMPLOYEE_VAULT=/app/vault
      - ODOO_URL=http://odoo:8069
      - ODOO_DB=ai_employee_db
      - ODOO_USER=admin
      - ODOO_PASSWORD=${ODOO_ADMIN_PASSWORD}
      - FACEBOOK_ACCESS_TOKEN=${FACEBOOK_ACCESS_TOKEN}
      - FACEBOOK_PAGE_ID=${FACEBOOK_PAGE_ID}
    volumes:
      - ./AI_Employee_Vault:/app/vault
      - ./logs:/app/logs
    command: python orchestrator.py daemon
    restart: unless-stopped

volumes:
  odoo-db-data:
  odoo-data:
```

### Step 1.2: Create Odoo Configuration

**Estimated:** 1 hour

```ini
; odoo-config/odoo.conf
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
; Database
proxy_mode = True
workers = 2
; Logging
logfile = /var/log/odoo/odoo.log
log_level = info
; Performance
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 600
limit_time_real = 1200
max_cron_threads = 2
```

### Step 1.3: Create Dockerfile for AI Employee

**Estimated:** 1 hour

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/vault

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

EXPOSE 8080

CMD ["python", "orchestrator.py", "daemon"]
```

### Step 1.4: Update requirements.txt

```
# Existing
google-auth>=2.22.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.1
google-api-python-client>=2.97.0
python-dotenv>=1.0.0
schedule>=1.2.0

# Gold Tier additions
requests>=2.31.0
xmlrpc-client>=1.0.0  # For Odoo XML-RPC (JSON-RPC uses requests)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.7
docker>=6.1.0
docker-compose>=1.29.0
```

---

## Phase 2: Odoo JSON-RPC MCP Server

### Step 2.1: Create MCP Server Structure

**File:** `mcp_servers/odoo_mcp.py`

**Estimated:** 4-5 hours

**Core Methods:**

| Method | Description | Odoo API Call |
|--------|-------------|---------------|
| `create_invoice` | Create customer invoice | `account.move` create |
| `get_account_summary` | Get P&L, Balance Sheet | `account.report` |
| `list_customers` | Get customer list | `res.partner` search_read |
| `create_customer` | Add new customer | `res.partner` create |
| `post_journal_entry` | Create manual journal entry | `account.move` create |
| `get_outstanding_invoices` | List unpaid invoices | `account.move` search_read |
| `reconcile_payment` | Match payment to invoice | `account.move` action_post |

**JSON-RPC Example:**
```python
# Odoo JSON-RPC connection
import json
import requests

class OdooJSONRPC:
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self._authenticate()
    
    def _authenticate(self):
        endpoint = f"{self.url}/jsonrpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [self.db, self.username, self.password]
            },
            "id": 1
        }
        response = requests.post(endpoint, json=payload)
        self.uid = response.json()["result"]
    
    def execute_kw(self, model, method, args=None, kwargs=None):
        endpoint = f"{self.url}/jsonrpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [self.db, self.uid, self.password, model, method, args or [], kwargs or {}]
            },
            "id": 2
        }
        response = requests.post(endpoint, json=payload)
        return response.json()["result"]
```

### Step 2.2: MCP Server Configuration

**File:** `mcp_servers/odoo_mcp.json`

```json
{
  "name": "odoo-mcp",
  "description": "Odoo 19+ Accounting MCP Server via JSON-RPC",
  "version": "1.0.0",
  "type": "mcp-server",
  "entrypoint": "python mcp_servers/odoo_mcp.py",
  "tools": [
    {
      "name": "create_invoice",
      "description": "Create a customer invoice in Odoo",
      "parameters": {
        "partner_id": "integer",
        "invoice_lines": "array",
        "date": "string (YYYY-MM-DD)"
      }
    },
    {
      "name": "get_account_summary",
      "description": "Get profit/loss and balance summary",
      "parameters": {
        "date_from": "string (YYYY-MM-DD)",
        "date_to": "string (YYYY-MM-DD)"
      }
    },
    {
      "name": "list_customers",
      "description": "List all customers from Odoo",
      "parameters": {
        "limit": "integer (default 100)"
      }
    },
    {
      "name": "create_customer",
      "description": "Create a new customer in Odoo",
      "parameters": {
        "name": "string",
        "email": "string",
        "phone": "string",
        "is_company": "boolean"
      }
    }
  ]
}
```

---

## Phase 3: Facebook/Instagram Integration

### Step 3.1: Graph API Integration

**File:** `mcp_servers/social_mcp.py`

**Estimated:** 3-4 hours

**Required Setup:**
1. Facebook Developer Account: https://developers.facebook.com/
2. Create App with "Pages" and "Instagram Basic Display" products
3. Get Page Access Token with `pages_manage_posts`, `instagram_content_publish` permissions
4. Connect Instagram Business Account to Facebook Page

**Core Methods:**

```python
# Facebook Graph API client
import requests

class FacebookGraphAPI:
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token, page_id):
        self.access_token = access_token
        self.page_id = page_id
    
    def post_to_page(self, message, link=None, image_url=None):
        """Post to Facebook Page"""
        endpoint = f"{self.BASE_URL}/{self.page_id}/feed"
        params = {
            "access_token": self.access_token,
            "message": message
        }
        if link:
            params["link"] = link
        if image_url:
            params["link"] = image_url
            
        response = requests.post(endpoint, params=params)
        return response.json()
    
    def get_page_insights(self, since, until):
        """Get page analytics"""
        endpoint = f"{self.BASE_URL}/{self.page_id}/insights"
        params = {
            "access_token": self.access_token,
            "metric": "page_impressions,page_engaged_users,page_fan_adds",
            "since": since,
            "until": until
        }
        response = requests.get(endpoint, params=params)
        return response.json()
    
    def post_to_instagram(self, image_url, caption):
        """Post to connected Instagram Business Account"""
        # First get Instagram Business Account ID from page
        ig_account_id = self._get_ig_account_id()
        
        # Create media container
        endpoint = f"{self.BASE_URL}/{ig_account_id}/media"
        params = {
            "access_token": self.access_token,
            "image_url": image_url,
            "caption": caption
        }
        response = requests.post(endpoint, params=params)
        creation_id = response.json()["id"]
        
        # Publish the container
        endpoint = f"{self.BASE_URL}/{ig_account_id}/media_publish"
        params = {
            "access_token": self.access_token,
            "creation_id": creation_id
        }
        response = requests.post(endpoint, params=params)
        return response.json()
```

### Step 3.2: Social Media Agent Skill

**File:** `.claude/skills/social-media.json`

```json
{
  "name": "social-media",
  "description": "Manage social media posts and analytics",
  "type": "agent-skill",
  "commands": {
    "generate-post": "Generate a social media post based on business context",
    "schedule-post": "Schedule a post for future publication",
    "post-approval": "Create HITL approval request for social media",
    "analytics": "Generate social media summary report"
  }
}
```

---

## Phase 4: Ralph Wiggum Autonomous Loop

### Step 4.1: Understanding the Pattern

The Ralph Wiggum Loop keeps Claude working autonomously until a task is complete.

**Workflow:**
```
1. Task arrives in /Needs_Action/
2. Orchestrator creates state file: /In_Progress/ralph_state_<task_id>.json
3. Claude starts processing
4. When Claude tries to exit:
   - Stop hook checks: Is task in /Done/?
   - NO → Block exit, re-inject prompt
   - YES → Allow exit
5. Repeat until complete or max iterations reached
```

### Step 4.2: Implementation

**File:** `ralph_loop.py`

**Estimated:** 4-5 hours

```python
#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Autonomous Task Completion
Keeps AI working until task is complete
"""

import json
import time
from pathlib import Path
from datetime import datetime

class RalphLoop:
    def __init__(self, vault_path, max_iterations=10, completion_promise="TASK_COMPLETE"):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.in_progress = self.vault_path / "In_Progress"
        self.done = self.vault_path / "Done"
        self.max_iterations = max_iterations
        self.completion_promise = completion_promise
        self.iteration = 0
        
        # Ensure directories exist
        self.in_progress.mkdir(exist_ok=True)
    
    def create_state_file(self, task_file, prompt):
        """Create state file for a new task"""
        task_id = task_file.stem
        state_file = self.in_progress / f"ralph_state_{task_id}.json"
        
        state = {
            "task_id": task_id,
            "task_file": str(task_file),
            "prompt": prompt,
            "created_at": datetime.now().isoformat(),
            "iteration": 0,
            "status": "in_progress",
            "history": []
        }
        
        state_file.write_text(json.dumps(state, indent=2))
        return state_file
    
    def check_completion(self, task_id):
        """Check if task is complete (file moved to /Done)"""
        # Check for completion marker in Done folder
        done_marker = self.done / f"{task_id}.md"
        complete_marker = self.in_progress / f"{task_id}.complete"
        
        return done_marker.exists() or complete_marker.exists()
    
    def should_continue(self, state_file):
        """Determine if loop should continue"""
        state = json.loads(state_file.read_text())
        task_id = state["task_id"]
        
        # Check if complete
        if self.check_completion(task_id):
            state["status"] = "completed"
            state_file.write_text(json.dumps(state, indent=2))
            return False
        
        # Check max iterations
        if state["iteration"] >= self.max_iterations:
            state["status"] = "max_iterations_reached"
            state_file.write_text(json.dumps(state, indent=2))
            return False
        
        return True
    
    def get_reinjection_prompt(self, state_file):
        """Generate prompt for next iteration"""
        state = json.loads(state_file.read_text())
        
        # Increment iteration
        state["iteration"] += 1
        state["last_updated"] = datetime.now().isoformat()
        
        # Build context from history
        history_context = "\n".join([
            f"Iteration {h['iteration']}: {h['action']}" 
            for h in state["history"][-3:]  # Last 3 actions
        ])
        
        reinjection = f"""
Previous work on task '{state['task_id']}':
{history_context}

Task is NOT complete. Continue working.
Original prompt: {state['prompt']}

Output '{self.completion_promise}' when done.
Current iteration: {state['iteration']}/{self.max_iterations}
"""
        
        state_file.write_text(json.dumps(state, indent=2))
        return reinjection
    
    def record_action(self, state_file, action, result):
        """Record an action in the history"""
        state = json.loads(state_file.read_text())
        state["history"].append({
            "iteration": state["iteration"],
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        state_file.write_text(json.dumps(state, indent=2))


class RalphStopHook:
    """
    Stop hook that intercepts Claude's exit and re-injects prompt
    This integrates with Claude Code's stop hook system
    """
    
    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.in_progress = self.vault_path / "In_Progress"
        self.loop = RalphLoop(vault_path)
    
    def on_stop(self):
        """Called when Claude tries to exit"""
        # Find active state files
        for state_file in self.in_progress.glob("ralph_state_*.json"):
            state = json.loads(state_file.read_text())
            
            if state["status"] == "in_progress":
                # Check if complete
                if self.loop.check_completion(state["task_id"]):
                    print(f"✅ Task {state['task_id']} complete. Exiting.")
                    return True  # Allow exit
                else:
                    # Re-inject prompt
                    print(f"⏳ Task {state['task_id']} not complete. Continuing...")
                    prompt = self.loop.get_reinjection_prompt(state_file)
                    print(f"\n{prompt}\n")
                    return False  # Block exit
        
        return True  # Allow exit if no active tasks
```

### Step 4.3: CLI Command

**Usage:**
```bash
# Start a Ralph loop on a task
python orchestrator.py ralph-loop --task TASK_001 --max-iterations 10

# Or use the skill
/claude skill ralph-loop "Process accounting reconciliation" --completion-promise "RECONCILE_COMPLETE"
```

---

## Phase 5: Multi-MCP Architecture

### Step 5.1: MCP Registry

**File:** `mcp_registry.py`

**Estimated:** 3-4 hours

```python
"""
Multi-MCP Server Registry and Router
Manages connections to multiple MCP servers
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

class MCPRegistry:
    """Registry of available MCP servers"""
    
    def __init__(self, config_path: str = "mcp_servers/mcp_config.json"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, dict] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self._load_config()
    
    def _load_config(self):
        """Load MCP server configurations"""
        if self.config_path.exists():
            self.servers = json.loads(self.config_path.read_text())
    
    def get_server(self, name: str) -> Optional[dict]:
        """Get MCP server configuration"""
        return self.servers.get(name)
    
    def start_server(self, name: str) -> bool:
        """Start an MCP server process"""
        config = self.get_server(name)
        if not config:
            return False
        
        try:
            process = subprocess.Popen(
                config["entrypoint"].split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=config.get("cwd", ".")
            )
            self.processes[name] = process
            return True
        except Exception as e:
            print(f"Failed to start {name}: {e}")
            return False
    
    def stop_server(self, name: str):
        """Stop an MCP server"""
        if name in self.processes:
            self.processes[name].terminate()
            del self.processes[name]
    
    def list_servers(self) -> list:
        """List all registered MCP servers"""
        return list(self.servers.keys())


class MCPRouter:
    """Routes requests to appropriate MCP servers"""
    
    def __init__(self, registry: MCPRegistry):
        self.registry = registry
        self.circuit_breakers = {}
    
    def call_tool(self, server_name: str, tool_name: str, **kwargs):
        """Call a tool on an MCP server with circuit breaker"""
        # Check circuit breaker
        if self._is_circuit_open(server_name):
            return {"error": f"Circuit breaker open for {server_name}"}
        
        try:
            # Route to appropriate server
            if server_name == "odoo":
                return self._call_odoo_tool(tool_name, **kwargs)
            elif server_name == "social":
                return self._call_social_tool(tool_name, **kwargs)
            elif server_name == "email":
                return self._call_email_tool(tool_name, **kwargs)
            else:
                return {"error": f"Unknown server: {server_name}"}
        except Exception as e:
            self._record_failure(server_name)
            return {"error": str(e)}
    
    def _is_circuit_open(self, server_name: str) -> bool:
        """Check if circuit breaker is open"""
        if server_name not in self.circuit_breakers:
            return False
        return self.circuit_breakers[server_name]["failures"] >= 3
    
    def _record_failure(self, server_name: str):
        """Record a failure for circuit breaker"""
        if server_name not in self.circuit_breakers:
            self.circuit_breakers[server_name] = {"failures": 0}
        self.circuit_breakers[server_name]["failures"] += 1
```

### Step 5.2: MCP Configuration

**File:** `mcp_servers/mcp_config.json`

```json
{
  "odoo": {
    "name": "odoo-mcp",
    "description": "Odoo 19+ Accounting MCP",
    "entrypoint": "python mcp_servers/odoo_mcp.py",
    "cwd": ".",
    "health_check": "http://localhost:8081/health",
    "fallback": "accounting_offline_mode"
  },
  "social": {
    "name": "social-mcp",
    "description": "Facebook/Instagram Social MCP",
    "entrypoint": "python mcp_servers/social_mcp.py",
    "cwd": ".",
    "health_check": "http://localhost:8082/health",
    "fallback": "social_queue_mode"
  },
  "email": {
    "name": "email-mcp",
    "description": "Email sending MCP",
    "entrypoint": "python mcp_servers/email_mcp.py",
    "cwd": ".",
    "health_check": "http://localhost:8083/health",
    "fallback": "email_queue_mode"
  }
}
```

---

## Phase 6: Weekly Business Audit & CEO Briefing

### Step 6.1: Audit Generator

**File:** `audit_generator.py`

**Estimated:** 3-4 hours

```python
"""
Weekly Business Audit and CEO Briefing Generator
Runs every Sunday night, delivers Monday morning CEO brief
"""

from datetime import datetime, timedelta
from pathlib import Path
import json

class CEOBriefingGenerator:
    def __init__(self, vault_path, odoo_client):
        self.vault_path = Path(vault_path)
        self.briefings_path = self.vault_path / "Briefings"
        self.briefings_path.mkdir(exist_ok=True)
        self.odoo = odoo_client
    
    def generate_weekly_briefing(self):
        """Generate CEO briefing for the past week"""
        today = datetime.now()
        week_start = today - timedelta(days=7)
        
        # Collect data
        accounting_data = self._get_accounting_summary(week_start, today)
        task_data = self._get_task_summary(week_start, today)
        goals_data = self._get_goals_progress()
        
        # Generate briefing
        briefing = self._create_briefing_document(
            week_start, today, accounting_data, task_data, goals_data
        )
        
        # Save to vault
        filename = f"CEO_Briefing_{today.strftime('%Y-%m-%d')}.md"
        filepath = self.briefings_path / filename
        filepath.write_text(briefing)
        
        return filepath
    
    def _get_accounting_summary(self, date_from, date_to):
        """Get accounting data from Odoo"""
        try:
            # Get invoices
            invoices = self.odoo.execute_kw(
                "account.move",
                "search_read",
                [[["invoice_date", ">=", date_from.strftime("%Y-%m-%d")],
                  ["invoice_date", "<=", date_to.strftime("%Y-%m-%d")],
                  ["move_type", "in", ["out_invoice", "out_refund"]]]],
                {"fields": ["name", "amount_total", "state", "invoice_date"]}
            )
            
            revenue = sum(inv["amount_total"] for inv in invoices if inv["move_type"] == "out_invoice")
            
            return {
                "revenue": revenue,
                "invoice_count": len(invoices),
                "unpaid_invoices": len([i for i in invoices if i["state"] == "posted"])
            }
        except Exception as e:
            return {"error": str(e), "revenue": 0}
    
    def _create_briefing_document(self, week_start, week_end, accounting, tasks, goals):
        """Create the CEO briefing document in Premium Dark Mode style"""
        
        return f"""---
title: CEO Weekly Briefing
period: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}
generated: {datetime.now().isoformat()}
type: weekly_briefing
---

# CEO Weekly Briefing
## Week of {week_start.strftime('%B %d, %Y')}

---

### Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| Revenue | ${accounting.get('revenue', 0):,.2f} | {'✅' if accounting.get('revenue', 0) > 0 else '⚠️'} |
| Tasks Completed | {tasks.get('completed', 0)} | 📊 |
| Outstanding Invoices | {accounting.get('unpaid_invoices', 0)} | {'⚠️' if accounting.get('unpaid_invoices', 0) > 5 else '✅'} |

---

### Financial Performance

**Revenue This Week:** ${accounting.get('revenue', 0):,.2f}

**Invoices Generated:** {accounting.get('invoice_count', 0)}

**Outstanding Payments:** {accounting.get('unpaid_invoices', 0)}

---

### Task Performance

**Completed:** {tasks.get('completed', 0)}
**Pending:** {tasks.get('pending', 0)}
**Overdue:** {tasks.get('overdue', 0)}

---

### Goal Progress

{self._format_goals(goals)}

---

### Bottlenecks Identified

{self._identify_bottlenecks(tasks, accounting)}

---

### Proactive Suggestions

{self._generate_suggestions(tasks, accounting)}

---

*Generated by AI Employee - Gold Tier Autonomous System*
*Next briefing: {(week_end + timedelta(days=7)).strftime('%Y-%m-%d')}*
"""
```

### Step 6.2: Schedule Weekly Audit

**Update to scheduler.py:**
```python
# Add to scheduled jobs
"weekly_ceo_briefing": {
    "name": "Weekly CEO Briefing",
    "schedule": "0 20 * * 0",  # Sunday at 8 PM
    "command": "python audit_generator.py",
    "description": "Generate weekly CEO briefing for Monday morning"
}
```

---

## Phase 7: Error Recovery & Audit Logging

### Step 7.1: Comprehensive Audit Logger

**File:** `audit_logger.py`

**Estimated:** 2-3 hours

```python
"""
Comprehensive Audit Logging System
Tracks all AI Employee actions for compliance and debugging
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

class AuditLogger:
    """Structured audit logging for all AI Employee actions"""
    
    def __init__(self, log_path: str = "AI_Employee_Vault/Logs"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        # Create daily log file
        self.current_log_file = self.log_path / f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        # Setup Python logger as well
        self.logger = logging.getLogger('AI_Employee_Audit')
    
    def log_event(self, event_type: str, details: Dict[str, Any], user_id: str = "ai_employee"):
        """Log an audit event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "source": "gold_tier_orchestrator"
        }
        
        # Append to JSONL file
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Also log to Python logger
        self.logger.info(f"[{event_type}] {json.dumps(details)}")
    
    def log_mcp_call(self, server: str, tool: str, params: dict, result: any, duration_ms: float):
        """Log an MCP server call"""
        self.log_event("mcp_call", {
            "server": server,
            "tool": tool,
            "params": params,
            "success": "error" not in str(result).lower(),
            "duration_ms": duration_ms
        })
    
    def log_ralph_iteration(self, task_id: str, iteration: int, action: str, result: str):
        """Log a Ralph Wiggum loop iteration"""
        self.log_event("ralph_iteration", {
            "task_id": task_id,
            "iteration": iteration,
            "action": action,
            "result": result
        })
    
    def log_task_completion(self, task_id: str, duration_seconds: float, success: bool):
        """Log task completion"""
        self.log_event("task_completion", {
            "task_id": task_id,
            "duration_seconds": duration_seconds,
            "success": success
        })
    
    def query_logs(self, date_from: datetime = None, date_to: datetime = None, 
                   event_type: str = None, limit: int = 100) -> list:
        """Query audit logs with filters"""
        events = []
        
        # Get all log files in range
        log_files = self.log_path.glob("audit_*.jsonl")
        
        for log_file in log_files:
            with open(log_file) as f:
                for line in f:
                    event = json.loads(line.strip())
                    
                    # Apply filters
                    if event_type and event["event_type"] != event_type:
                        continue
                    
                    events.append(event)
        
        # Sort by timestamp and limit
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:limit]
```

### Step 7.2: Error Recovery System

**File:** `error_recovery.py`

```python
"""
Error Recovery and Resilience System
Handles failures gracefully with retry logic and circuit breakers
"""

import time
import random
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker pattern for MCP calls"""
    
    def __init__(self, name: str, failure_threshold: int = 3, 
                 recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        if not self.last_failure_time:
            return True
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


class RetryWithBackoff:
    """Retry mechanism with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with jitter"""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        # Add jitter (±20%)
        jitter = delay * 0.2 * (2 * random.random() - 1)
        return delay + jitter


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
```

---

## Phase 8: Updated Orchestrator (Gold Tier)

### Key Changes to orchestrator.py

**Estimated:** 3-4 hours

```python
#!/usr/bin/env python3
"""
AI Employee Orchestrator - GOLD TIER
Master process with Ralph Loop, Multi-MCP, and Autonomous capabilities
"""

# ... existing imports ...

# Gold Tier imports
from ralph_loop import RalphLoop, RalphStopHook
from mcp_registry import MCPRegistry, MCPRouter
from audit_logger import AuditLogger
from error_recovery import CircuitBreaker, RetryWithBackoff
from audit_generator import CEOBriefingGenerator

class GoldTierOrchestrator:
    """Gold Tier orchestrator with autonomous capabilities"""
    
    def __init__(self):
        self.vault_path = self._get_vault_path()
        self.audit_logger = AuditLogger(str(self.vault_path / "Logs"))
        
        # Initialize MCP systems
        self.mcp_registry = MCPRegistry()
        self.mcp_router = MCPRouter(self.mcp_registry)
        
        # Initialize Ralph Loop
        self.ralph_loop = RalphLoop(self.vault_path)
        self.stop_hook = RalphStopHook(self.vault_path)
        
        # Initialize Gold Tier watchers
        self.watchers = []
        self._init_gold_watchers()
    
    def _init_gold_watchers(self):
        """Initialize Gold Tier watchers (Odoo, Social)"""
        # Odoo watcher for accounting events
        # Facebook/Instagram watcher for social notifications
        # ... implementation ...
        pass
    
    def run_autonomous_cycle(self):
        """Run one autonomous cycle with Ralph Loop"""
        # 1. Check for new tasks
        # 2. For each task, start Ralph Loop
        # 3. Process until complete or max iterations
        # 4. Log all actions
        pass
    
    def generate_ceo_briefing(self):
        """Generate weekly CEO briefing"""
        generator = CEOBriefingGenerator(self.vault_path, self._get_odoo_client())
        return generator.generate_weekly_briefing()


def main():
    """Updated main with Gold Tier commands"""
    parser = argparse.ArgumentParser(description='AI Employee Orchestrator - GOLD TIER')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'start', 'daemon', 'ralph-loop', 
                                'ceo-briefing', 'mcp-status', 'audit-logs'])
    
    # Add Gold Tier specific args
    parser.add_argument('--task', help='Task ID for Ralph Loop')
    parser.add_argument('--max-iterations', type=int, default=10)
    parser.add_argument('--completion-promise', default='TASK_COMPLETE')
    
    args = parser.parse_args()
    
    orchestrator = GoldTierOrchestrator()
    
    if args.command == 'ralph-loop':
        # Start Ralph Loop on specific task
        if not args.task:
            print("Error: --task required for ralph-loop")
            return
        # ... implementation ...
    
    elif args.command == 'ceo-briefing':
        filepath = orchestrator.generate_ceo_briefing()
        print(f"CEO Briefing generated: {filepath}")
    
    elif args.command == 'daemon':
        # Run continuous autonomous mode
        print("Starting Gold Tier autonomous daemon...")
        while True:
            orchestrator.run_autonomous_cycle()
            time.sleep(60)


if __name__ == '__main__':
    main()
```

---

## Implementation Schedule

| Phase | Task | Hours | Cumulative |
|-------|------|-------|------------|
| 1 | Docker Compose + Odoo 19 | 4-5 | 4-5 |
| 2 | Odoo JSON-RPC MCP Server | 4-5 | 8-10 |
| 3 | Facebook/Instagram Integration | 3-4 | 11-14 |
| 4 | Ralph Wiggum Loop | 4-5 | 15-19 |
| 5 | Multi-MCP Architecture | 3-4 | 18-23 |
| 6 | Weekly Business Audit | 3-4 | 21-27 |
| 7 | Audit Logging + Error Recovery | 2-3 | 23-30 |
| 8 | Integration Testing | 4-6 | 27-36 |
| 9 | Documentation | 2-4 | 29-40 |

**Total Estimated: 40 hours**

---

## Environment Variables Required

```bash
# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=ai_employee_db
ODOO_USER=admin
ODOO_PASSWORD=your_secure_password
ODOO_ADMIN_PASSWORD=your_admin_password

# Facebook/Instagram
FACEBOOK_ACCESS_TOKEN=your_long_lived_token
FACEBOOK_PAGE_ID=your_page_id
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_ig_account_id

# Existing (Silver Tier)
AI_EMPLOYEE_VAULT=./AI_Employee_Vault
GMAIL_CREDENTIALS_PATH=./credentials.json
```

---

## Success Criteria

Gold Tier is complete when:

- [ ] `docker-compose up` starts Odoo 19+ with PostgreSQL
- [ ] Odoo MCP server can create invoices and get accounting summaries
- [ ] Facebook/Instagram posts can be created with HITL approval
- [ ] Ralph Loop completes multi-step tasks autonomously
- [ ] Weekly CEO briefing generates automatically with business insights
- [ ] All actions are logged to structured audit logs
- [ ] Circuit breakers prevent cascade failures
- [ ] System gracefully degrades when services are unavailable
- [ ] All functionality is exposed as Agent Skills

---

## Next Steps

1. **Review this plan** and confirm scope
2. **Start Phase 1**: Docker Compose setup
3. **Set up Odoo**: Initialize Odoo database and configure chart of accounts
4. **Get Facebook Developer credentials**: Create app, get tokens
5. **Implement sequentially**: Each phase builds on the previous

Ready to begin Phase 1?