#!/usr/bin/env python3
"""
Test Odoo JSON-RPC Connection
=============================
Verify connectivity with the self-hosted Odoo 19 container.
Run this after starting Docker Compose to ensure Odoo is ready.

Usage:
    python test_odoo_connection.py
    python test_odoo_connection.py --demo

Prerequisites:
    - Docker Compose is running: docker-compose up -d
    - Odoo container is healthy: docker-compose ps
"""

import os
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp_servers.odoo_mcp import OdooMCP, OdooConfig, OdooJSONRPCClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Ensure mcp_servers/odoo_mcp.py exists")
    sys.exit(1)


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_section(title):
    """Print section header"""
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print("─"*60)


def test_basic_connection():
    """Test basic JSON-RPC connection"""
    print_section("Test 1: Basic Connection")

    print("🔌 Connecting to Odoo JSON-RPC endpoint...")

    try:
        mcp = OdooMCP()

        if not mcp.client:
            print("❌ FAILED: Could not initialize connection")
            return False

        print("✅ Connection initialized")

        # Test authentication
        result = mcp.client.test_connection()

        if result.get('status') == 'connected':
            print(f"✅ Authentication successful")
            print(f"   UID: {result['uid']}")
            print(f"   User: {result.get('user', {}).get('name', 'Unknown')}")
            print(f"   Database: {result['database']}")
            return True
        else:
            print(f"❌ Authentication failed: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_customer_operations():
    """Test customer CRUD operations"""
    print_section("Test 2: Customer Operations")

    mcp = OdooMCP()
    if not mcp.client:
        print("❌ Not connected")
        return False

    # Test list customers
    print("🔍 Testing: list_customers()")
    result = mcp.list_customers(limit=5)

    if 'error' in result:
        print(f"❌ FAILED: {result['error']}")
        return False

    print(f"✅ Retrieved {result['count']} customers")
    if result['customers']:
        cust = result['customers'][0]
        print(f"   Sample: {cust['name']} (ID: {cust['id']})")

    # Test create customer (demo mode only)
    print("\n📝 Testing: create_customer()")
    print("   (Skipping in test mode - requires demo flag)")

    return True


def test_invoice_operations():
    """Test invoice creation and listing"""
    print_section("Test 3: Invoice Operations")

    mcp = OdooMCP()
    if not mcp.client:
        print("❌ Not connected")
        return False

    # Test outstanding invoices
    print("💰 Testing: get_outstanding_invoices()")
    result = mcp.get_outstanding_invoices()

    if 'error' in result:
        print(f"❌ FAILED: {result['error']}")
        return False

    print(f"✅ Retrieved outstanding invoices")
    print(f"   Count: {result['count']}")
    print(f"   Total Outstanding: ${result['total_outstanding']:,.2f}")

    if result['invoices']:
        inv = result['invoices'][0]
        print(f"   First: {inv['name']} - ${inv['amount_residual']:,.2f}")

    return True


def test_account_summary():
    """Test account summary retrieval"""
    print_section("Test 4: Account Summary")

    mcp = OdooMCP()
    if not mcp.client:
        print("❌ Not connected")
        return False

    print("📊 Testing: get_account_summary()")
    result = mcp.get_account_summary()

    if 'error' in result:
        print(f"❌ FAILED: {result['error']}")
        return False

    print(f"✅ Retrieved account summary")
    summary = result['summary']
    print(f"\n   Period: {result['period']['from']} to {result['period']['to']}")
    print(f"   Revenue: ${summary['total_revenue']:,.2f}")
    print(f"   Expenses: ${summary['total_expenses']:,.2f}")
    print(f"   Net Profit: ${summary['net_profit']:,.2f}")
    print(f"   Outstanding: ${summary['outstanding']:,.2f}")

    return True


def run_demonstation():
    """Run full demonstration with sample data"""
    print_header("ODDEMO DEMONSTRATION")
    print("\nThis will create sample data in your Odoo instance.")
    print("Make sure you're in a development environment!\n")

    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Demo cancelled.")
        return

    mcp = OdooMCP()
    if not mcp.client:
        print("❌ Not connected to Odoo")
        return

    # Create a sample customer
    print("\n📝 Creating sample customer...")
    customer_result = mcp.create_customer(
        name="AI Employee Demo Customer",
        email="demo@aiemployee.local",
        phone="+1-555-AI-EMPLOYEE",
        is_company=False
    )

    if 'error' in customer_result:
        print(f"❌ Failed: {customer_result['error']}")
        return

    customer_id = customer_result['customer_id']
    print(f"✅ Created customer: {customer_result['name']} (ID: {customer_id})")

    # Create a sample invoice
    print("\n🧾 Creating sample invoice...")
    invoice_lines = [
        {
            'description': 'AI Employee Consultation - Gold Tier Setup',
            'quantity': 1,
            'price_unit': 2500.00
        },
        {
            'description': 'Ralph Wiggum Loop Implementation',
            'quantity': 1,
            'price_unit': 1500.00
        }
    ]

    invoice_result = mcp.create_invoice(
        partner_id=customer_id,
        invoice_lines=invoice_lines
    )

    if 'error' in invoice_result:
        print(f"❌ Failed: {invoice_result['error']}")
        return

    print(f"✅ Created invoice: {invoice_result['invoice_number']}")
    print(f"   Amount: ${invoice_result['amount_total']:,.2f}")
    print(f"   Status: {invoice_result['state']}")

    # Get updated summary
    print("\n📊 Getting updated account summary...")
    summary_result = mcp.get_account_summary()
    if 'error' not in summary_result:
        print(f"✅ New total revenue: ${summary_result['summary']['total_revenue']:,.2f}")

    print("\n✨ Demo complete!")


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Odoo Connection')
    parser.add_argument('--demo', action='store_true',
                        help='Run demonstration with sample data')
    parser.add_argument('--wait', type=int, default=0,
                        help='Wait seconds before testing (for container startup)')

    args = parser.parse_args()

    print_header("ODOO JSON-RPC CONNECTION TEST")
    print("Gold Tier: Accounting Integration\n")

    # Show configuration
    print("Configuration:")
    print(f"  ODOO_URL: {os.getenv('ODOO_URL', 'http://localhost:8069')}")
    print(f"  ODOO_DB: {os.getenv('ODOO_DB', 'ai_employee_db')}")
    print(f"  ODOO_USER: {os.getenv('ODOO_USER', 'admin')}")
    print(f"  ODOO_PASSWORD: {'*' * len(os.getenv('ODOO_PASSWORD', ''))}")

    # Wait if requested
    if args.wait > 0:
        print(f"\n⏳ Waiting {args.wait} seconds for Odoo to start...")
        time.sleep(args.wait)

    # Run demo or tests
    if args.demo:
        run_demonstation()
    else:
        # Run all tests
        tests = [
            ("Basic Connection", test_basic_connection),
            ("Customer Operations", test_customer_operations),
            ("Invoice Operations", test_invoice_operations),
            ("Account Summary", test_account_summary),
        ]

        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                print(f"\n❌ {name} failed with exception: {e}")
                results.append((name, False))

        # Summary
        print_header("TEST SUMMARY")
        passed = sum(1 for _, s in results if s)
        total = len(results)

        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {name}")

        print(f"\n  Result: {passed}/{total} tests passed")

        if passed == total:
            print("\n  🎉 All tests passed! Odoo integration is ready.")
            return 0
        else:
            print("\n  ⚠️  Some tests failed. Check the logs above.")
            print("\n  Troubleshooting:")
            print("    1. Ensure Docker Compose is running: docker-compose up -d")
            print("    2. Check Odoo is healthy: docker-compose logs odoo")
            print("    3. Verify credentials in .env file")
            print("    4. Wait for Odoo to fully initialize (may take 2-3 minutes)")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
