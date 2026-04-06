#!/usr/bin/env python3
"""
Odoo MCP Server - GOLD TIER
============================
Model Context Protocol (MCP) server for Odoo 19+ JSON-RPC integration.
Provides accounting and business management capabilities for the AI Employee.

Features:
- JSON-RPC connection to self-hosted Odoo
- Customer management (res.partner)
- Invoice creation (account.move)
- Journal entries (account.move)
- Account summaries and reports
- Secure credential handling via environment variables

Usage:
    python mcp_servers/odoo_mcp.py

Environment Variables:
    ODOO_URL - Odoo instance URL (default: http://localhost:8069)
    ODOO_DB - Database name (default: ai_employee_db)
    ODOO_USER - Username (default: admin)
    ODOO_PASSWORD - Password
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, asdict

# Configure logging with Premium Dark Mode aesthetic
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/odoo_mcp.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('OdooMCP')


@dataclass
class OdooConfig:
    """Configuration for Odoo connection"""
    url: str = "http://localhost:8069"
    db: str = "ai_employee_db"
    username: str = "admin"
    password: str = "admin"

    @classmethod
    def from_env(cls) -> 'OdooConfig':
        """Load configuration from environment variables"""
        return cls(
            url=os.getenv('ODOO_URL', 'http://localhost:8069'),
            db=os.getenv('ODOO_DB', 'ai_employee_db'),
            username=os.getenv('ODOO_USER', 'admin'),
            password=os.getenv('ODOO_PASSWORD', 'admin')
        )


class OdooJSONRPCClient:
    """
    JSON-RPC client for Odoo 19+

    Handles authentication and method execution via Odoo's JSON-RPC endpoint.
    All communication is stateless; uid is stored after authentication.
    """

    def __init__(self, config: Optional[OdooConfig] = None):
        self.config = config or OdooConfig.from_env()
        self.uid: Optional[int] = None
        self.session = requests.Session()
        self._authenticate()

    def _get_endpoint(self) -> str:
        """Get JSON-RPC endpoint URL"""
        return f"{self.config.url.rstrip('/')}/jsonrpc"

    def _authenticate(self) -> bool:
        """
        Authenticate with Odoo and obtain user ID (uid)

        Returns:
            True if authentication successful, False otherwise
        """
        endpoint = self._get_endpoint()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [
                    self.config.db,
                    self.config.username,
                    self.config.password
                ]
            },
            "id": 1
        }

        try:
            logger.info(f"Authenticating with Odoo at {self.config.url}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if 'error' in result:
                logger.error(f"Authentication failed: {result['error']}")
                return False

            self.uid = result.get('result')
            if self.uid:
                logger.info(f"✅ Authenticated successfully (UID: {self.uid})")
                return True
            else:
                logger.error("Authentication returned empty UID")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Connection failed: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return False

    def execute_kw(self, model: str, method: str,
                   args: List = None, kwargs: Dict = None) -> Any:
        """
        Execute a method on an Odoo model

        Args:
            model: Odoo model name (e.g., 'res.partner', 'account.move')
            method: Method to execute (e.g., 'search_read', 'create', 'write')
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Result from Odoo, or None if error
        """
        if not self.uid:
            logger.error("Not authenticated")
            return None

        endpoint = self._get_endpoint()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.config.db,
                    self.uid,
                    self.config.password,
                    model,
                    method,
                    args or [],
                    kwargs or {}
                ]
            },
            "id": 2
        }

        try:
            response = self.session.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            if 'error' in result:
                error = result['error']
                logger.error(f"Odoo error: {error}")
                raise OdooRPCError(f"{error.get('message', 'Unknown error')}: {error.get('data', {}).get('debug', '')}")

            return result.get('result')

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise OdooRPCError(f"Connection failed: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test connection and return basic info"""
        try:
            # Get database info
            version_info = self.execute_kw('res.users', 'search_read',
                                          [[['id', '=', self.uid]]],
                                          {'fields': ['name', 'login', 'company_id']})

            return {
                "status": "connected",
                "uid": self.uid,
                "url": self.config.url,
                "database": self.config.db,
                "user": version_info[0] if version_info else None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class OdooRPCError(Exception):
    """Custom exception for Odoo RPC errors"""
    pass


class OdooMCP:
    """
    Model Context Protocol Server for Odoo

    Provides high-level accounting and business operations:
    - Customer Management
    - Invoice Creation
    - Account Summaries
    - Journal Entries
    """

    def __init__(self):
        self.client: Optional[OdooJSONRPCClient] = None
        self._connect()

    def _connect(self):
        """Initialize connection to Odoo"""
        try:
            self.client = OdooJSONRPCClient()
            logger.info("✅ Odoo MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Odoo MCP: {e}")
            self.client = None

    # ============================================================
    # CUSTOMER MANAGEMENT
    # ============================================================

    def list_customers(self, limit: int = 100,
                       search_term: str = None) -> Dict[str, Any]:
        """
        List customers from Odoo

        Args:
            limit: Maximum number of customers to return
            search_term: Optional search filter for name or email

        Returns:
            Dictionary with customers list and metadata
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            domain = [['customer_rank', '>', 0]]
            if search_term:
                domain = ['|', ['name', 'ilike', search_term],
                         ['email', 'ilike', search_term]]

            customers = self.client.execute_kw(
                'res.partner',
                'search_read',
                [domain],
                {
                    'fields': ['id', 'name', 'email', 'phone', 'mobile',
                              'street', 'city', 'zip', 'country_id',
                              'customer_rank', 'write_date'],
                    'limit': limit,
                    'order': 'name ASC'
                }
            )

            return {
                "status": "success",
                "count": len(customers),
                "customers": customers
            }

        except OdooRPCError as e:
            logger.error(f"Failed to list customers: {e}")
            return {"error": str(e)}

    def create_customer(self, name: str, email: str = None,
                       phone: str = None, is_company: bool = False,
                       **kwargs) -> Dict[str, Any]:
        """
        Create a new customer in Odoo

        Args:
            name: Customer name (required)
            email: Customer email
            phone: Customer phone
            is_company: True if this is a company
            **kwargs: Additional fields

        Returns:
            Dictionary with created customer ID
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            values = {
                'name': name,
                'customer_rank': 1,
                'is_company': is_company
            }
            if email:
                values['email'] = email
            if phone:
                values['phone'] = phone
            values.update(kwargs)

            customer_id = self.client.execute_kw(
                'res.partner',
                'create',
                [values]
            )

            logger.info(f"Created customer: {name} (ID: {customer_id})")

            return {
                "status": "success",
                "customer_id": customer_id,
                "name": name
            }

        except OdooRPCError as e:
            logger.error(f"Failed to create customer: {e}")
            return {"error": str(e)}

    # ============================================================
    # INVOICE MANAGEMENT
    # ============================================================

    def create_invoice(self, partner_id: int, invoice_lines: List[Dict],
                      invoice_date: str = None, due_date: str = None,
                      invoice_type: str = 'out_invoice') -> Dict[str, Any]:
        """
        Create a customer invoice in Odoo

        Args:
            partner_id: Customer ID (res.partner)
            invoice_lines: List of line items with product, quantity, price
                Example: [{'product_id': 1, 'quantity': 2, 'price_unit': 100.00}]
            invoice_date: Invoice date (YYYY-MM-DD), defaults to today
            due_date: Due date (YYYY-MM-DD)
            invoice_type: 'out_invoice' (customer) or 'in_invoice' (vendor)

        Returns:
            Dictionary with invoice ID and details
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            # Validate partner exists
            partner = self.client.execute_kw(
                'res.partner', 'search_read',
                [[['id', '=', partner_id]]],
                {'fields': ['name'], 'limit': 1}
            )

            if not partner:
                return {"error": f"Customer with ID {partner_id} not found"}

            # Set dates
            today = datetime.now().strftime('%Y-%m-%d')
            invoice_date = invoice_date or today
            if not due_date:
                due = datetime.now() + timedelta(days=30)
                due_date = due.strftime('%Y-%m-%d')

            # Build invoice lines
            line_values = []
            total = 0.0

            for line in invoice_lines:
                line_val = {
                    'product_id': line.get('product_id'),
                    'name': line.get('description', 'Service'),
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0.0),
                }
                if line.get('tax_ids'):
                    line_val['tax_ids'] = [(6, 0, line['tax_ids'])]

                line_values.append((0, 0, line_val))
                total += line_val['quantity'] * line_val['price_unit']

            # Create invoice
            invoice_vals = {
                'partner_id': partner_id,
                'move_type': invoice_type,
                'invoice_date': invoice_date,
                'invoice_date_due': due_date,
                'invoice_line_ids': line_values,
            }

            invoice_id = self.client.execute_kw(
                'account.move',
                'create',
                [invoice_vals]
            )

            # Get invoice details
            invoice = self.client.execute_kw(
                'account.move',
                'search_read',
                [[['id', '=', invoice_id]]],
                {'fields': ['name', 'amount_total', 'state'], 'limit': 1}
            )

            logger.info(f"Created invoice {invoice[0].get('name')} for {partner[0]['name']}")

            return {
                "status": "success",
                "invoice_id": invoice_id,
                "invoice_number": invoice[0].get('name'),
                "partner_name": partner[0]['name'],
                "amount_total": invoice[0].get('amount_total'),
                "state": invoice[0].get('state')
            }

        except OdooRPCError as e:
            logger.error(f"Failed to create invoice: {e}")
            return {"error": str(e)}

    def get_outstanding_invoices(self, partner_id: int = None) -> Dict[str, Any]:
        """
        Get list of unpaid/outstanding invoices

        Args:
            partner_id: Optional filter by customer ID

        Returns:
            Dictionary with invoices list
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            domain = [
                ['move_type', '=', 'out_invoice'],
                ['state', '=', 'posted'],
                ['payment_state', 'in', ['not_paid', 'partial']]
            ]
            if partner_id:
                domain.append(['partner_id', '=', partner_id])

            invoices = self.client.execute_kw(
                'account.move',
                'search_read',
                [domain],
                {
                    'fields': ['id', 'name', 'partner_id', 'invoice_date',
                              'invoice_date_due', 'amount_total',
                              'amount_residual', 'state'],
                    'order': 'invoice_date_due ASC'
                }
            )

            total_outstanding = sum(inv.get('amount_residual', 0) for inv in invoices)

            return {
                "status": "success",
                "count": len(invoices),
                "total_outstanding": total_outstanding,
                "invoices": invoices
            }

        except OdooRPCError as e:
            logger.error(f"Failed to get outstanding invoices: {e}")
            return {"error": str(e)}

    # ============================================================
    # ACCOUNT SUMMARY
    # ============================================================

    def get_account_summary(self, date_from: str = None,
                           date_to: str = None) -> Dict[str, Any]:
        """
        Get account summary (P&L, Balance) for a period

        Args:
            date_from: Start date (YYYY-MM-DD), defaults to 30 days ago
            date_to: End date (YYYY-MM-DD), defaults to today

        Returns:
            Dictionary with revenue, expenses, and balance
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            # Set default date range
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')
            if not date_from:
                from_date = datetime.now() - timedelta(days=30)
                date_from = from_date.strftime('%Y-%m-%d')

            # Get posted invoices in date range
            domain = [
                ['move_type', '=', 'out_invoice'],
                ['state', '=', 'posted'],
                ['invoice_date', '>=', date_from],
                ['invoice_date', '<=', date_to]
            ]

            invoices = self.client.execute_kw(
                'account.move',
                'search_read',
                [domain],
                {'fields': ['amount_total', 'amount_residual']}
            )

            total_revenue = sum(inv.get('amount_total', 0) for inv in invoices)
            total_paid = sum(inv.get('amount_total', 0) - inv.get('amount_residual', 0)
                           for inv in invoices)

            # Get vendor bills (expenses)
            domain_bills = [
                ['move_type', '=', 'in_invoice'],
                ['state', '=', 'posted'],
                ['invoice_date', '>=', date_from],
                ['invoice_date', '<=', date_to]
            ]

            bills = self.client.execute_kw(
                'account.move',
                'search_read',
                [domain_bills],
                {'fields': ['amount_total']}
            )

            total_expenses = sum(bill.get('amount_total', 0) for bill in bills)

            return {
                "status": "success",
                "period": {
                    "from": date_from,
                    "to": date_to
                },
                "summary": {
                    "total_invoices": len(invoices),
                    "total_revenue": total_revenue,
                    "total_collected": total_paid,
                    "outstanding": total_revenue - total_paid,
                    "total_expenses": total_expenses,
                    "net_profit": total_revenue - total_expenses
                }
            }

        except OdooRPCError as e:
            logger.error(f"Failed to get account summary: {e}")
            return {"error": str(e)}

    # ============================================================
    # JOURNAL ENTRIES
    # ============================================================

    def post_journal_entry(self, lines: List[Dict],
                          ref: str = None) -> Dict[str, Any]:
        """
        Post a manual journal entry

        Args:
            lines: List of journal entry lines with account, debit, credit
            ref: Reference/memo for the entry

        Returns:
            Dictionary with move ID
        """
        if not self.client:
            return {"error": "Not connected to Odoo"}

        try:
            # Build move lines
            line_values = []
            for line in lines:
                line_val = {
                    'account_id': line['account_id'],
                    'debit': line.get('debit', 0.0),
                    'credit': line.get('credit', 0.0),
                    'name': line.get('name', ref or 'Journal Entry'),
                }
                if line.get('partner_id'):
                    line_val['partner_id'] = line['partner_id']
                line_values.append((0, 0, line_val))

            # Create journal entry
            move_vals = {
                'move_type': 'entry',
                'ref': ref or 'Manual Entry',
                'line_ids': line_values,
            }

            move_id = self.client.execute_kw(
                'account.move',
                'create',
                [move_vals]
            )

            # Post the entry
            self.client.execute_kw(
                'account.move',
                'action_post',
                [[move_id]]
            )

            logger.info(f"Posted journal entry: {move_id}")

            return {
                "status": "success",
                "move_id": move_id,
                "reference": ref
            }

        except OdooRPCError as e:
            logger.error(f"Failed to post journal entry: {e}")
            return {"error": str(e)}


# ============================================================
# MCP SERVER INTERFACE
# ============================================================

def main():
    """Run Odoo MCP Server"""
    import argparse

    parser = argparse.ArgumentParser(description='Odoo MCP Server')
    parser.add_argument('command', nargs='?',
                        choices=['test', 'list-customers', 'create-invoice',
                                'summary', 'outstanding', 'server'],
                        default='test',
                        help='Command to run')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limit for list operations')
    parser.add_argument('--partner-id', type=int,
                        help='Customer ID for invoice creation')

    args = parser.parse_args()

    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)

    print("="*60)
    print("🧮 ODOO MCP SERVER - GOLD TIER")
    print("="*60)

    # Initialize MCP
    mcp = OdooMCP()

    if not mcp.client:
        print("\n❌ Failed to connect to Odoo")
        print("   Check your .env file and ensure Odoo is running:")
        print("   docker-compose up -d odoo")
        return 1

    if args.command == 'test':
        # Test connection
        print("\n📊 Testing Odoo Connection...")
        result = mcp.client.test_connection()
        print(f"\nConnection Status: {result.get('status')}")
        print(f"Database: {result.get('database')}")
        print(f"User: {result.get('user', {}).get('name', 'Unknown')}")

    elif args.command == 'list-customers':
        print(f"\n👥 Listing customers (limit: {args.limit})...")
        result = mcp.list_customers(limit=args.limit)
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\nFound {result['count']} customers:")
            for cust in result['customers']:
                print(f"  • {cust['name']} (ID: {cust['id']})")
                if cust.get('email'):
                    print(f"    Email: {cust['email']}")

    elif args.command == 'summary':
        print("\n📈 Getting account summary...")
        result = mcp.get_account_summary()
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            summary = result['summary']
            print(f"\nPeriod: {result['period']['from']} to {result['period']['to']}")
            print(f"Total Revenue: ${summary['total_revenue']:,.2f}")
            print(f"Total Expenses: ${summary['total_expenses']:,.2f}")
            print(f"Net Profit: ${summary['net_profit']:,.2f}")
            print(f"Outstanding: ${summary['outstanding']:,.2f}")

    elif args.command == 'outstanding':
        print("\n💰 Getting outstanding invoices...")
        result = mcp.get_outstanding_invoices()
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\nOutstanding: ${result['total_outstanding']:,.2f}")
            print(f"Invoices: {result['count']}")
            for inv in result['invoices'][:5]:
                print(f"  • {inv['name']}: ${inv['amount_residual']:,.2f}")

    elif args.command == 'create-invoice':
        if not args.partner_id:
            print("❌ --partner-id required")
            return 1

        print(f"\n📝 Creating invoice for partner {args.partner_id}...")
        lines = [
            {'description': 'Consulting Services', 'quantity': 1, 'price_unit': 1000.00}
        ]
        result = mcp.create_invoice(args.partner_id, lines)
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\n✅ Invoice created:")
            print(f"   Number: {result['invoice_number']}")
            print(f"   Amount: ${result['amount_total']:,.2f}")

    print("\n" + "="*60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
