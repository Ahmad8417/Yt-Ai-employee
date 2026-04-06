#!/usr/bin/env python3
"""
Social MCP Server - GOLD TIER
==============================
Facebook and Instagram Graph API integration for the AI Employee.
Manages social media posting and analytics.

Features:
- Post to Facebook Pages
- Post to Instagram Business accounts
- Get page/analytics insights
- Human-in-the-Loop approval for all posts
- Comprehensive audit logging

Prerequisites:
1. Facebook Developer Account: https://developers.facebook.com/
2. Create an App with 'Pages' and 'Instagram Basic Display' products
3. Generate Page Access Token with permissions:
   - pages_manage_posts
   - pages_read_engagement
   - instagram_basic
   - instagram_content_publish

Environment Variables:
    FACEBOOK_ACCESS_TOKEN - Long-lived page access token
    FACEBOOK_PAGE_ID - Facebook Page ID to post to
    INSTAGRAM_BUSINESS_ACCOUNT_ID - Connected Instagram Business Account ID

Usage:
    python mcp_servers/social_mcp.py

    # Test connection
    python mcp_servers/social_mcp.py test

    # Post to Facebook
    python mcp_servers/social_mcp.py post-facebook --message "Hello World"

    # Get insights
    python mcp_servers/social_mcp.py insights
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SocialMCP')


@dataclass
class SocialConfig:
    """Configuration for Social Media APIs"""
    access_token: str
    page_id: str
    instagram_account_id: Optional[str] = None
    api_version: str = "v18.0"

    @classmethod
    def from_env(cls) -> 'SocialConfig':
        """Load configuration from environment variables"""
        return cls(
            access_token=os.getenv('FACEBOOK_ACCESS_TOKEN', ''),
            page_id=os.getenv('FACEBOOK_PAGE_ID', ''),
            instagram_account_id=os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID'),
            api_version=os.getenv('FACEBOOK_API_VERSION', 'v18.0')
        )

    def is_configured(self) -> bool:
        """Check if required configuration is present"""
        return bool(self.access_token and self.page_id)


class FacebookGraphAPI:
    """
    Facebook Graph API Client

    Handles authentication and API calls for Facebook Pages and Instagram Business.
    """

    BASE_URL = "https://graph.facebook.com"

    def __init__(self, config: Optional[SocialConfig] = None):
        self.config = config or SocialConfig.from_env()
        self.session = requests.Session()

    def _get_url(self, endpoint: str) -> str:
        """Build full API URL"""
        return f"{self.BASE_URL}/{self.config.api_version}/{endpoint}"

    def _make_request(self, method: str, endpoint: str,
                     params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        if not self.config.is_configured():
            return {"error": "Facebook credentials not configured"}

        url = self._get_url(endpoint)
        request_params = params or {}
        request_params['access_token'] = self.config.access_token

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=request_params, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=request_params, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=request_params, timeout=30)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return {"error": "Invalid response from Facebook API"}

    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and token validity"""
        if not self.config.is_configured():
            return {
                "status": "not_configured",
                "message": "FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID not set"
            }

        # Test by getting page info
        result = self._make_request('GET', f"{self.config.page_id}",
                                   params={'fields': 'name,id,category'})

        if 'error' in result:
            return {
                "status": "error",
                "error": result['error']
            }

        return {
            "status": "connected",
            "page_name": result.get('name'),
            "page_id": result.get('id'),
            "category": result.get('category'),
            "api_version": self.config.api_version
        }

    def post_to_page(self, message: str, link: str = None,
                    image_url: str = None) -> Dict[str, Any]:
        """
        Post to Facebook Page

        Args:
            message: Post text content
            link: Optional link to include
            image_url: Optional image URL to attach

        Returns:
            API response with post ID
        """
        endpoint = f"{self.config.page_id}/feed"

        params = {'message': message}
        if link:
            params['link'] = link
        if image_url:
            # For image posts, use /photos endpoint instead
            endpoint = f"{self.config.page_id}/photos"
            params['url'] = image_url

        logger.info(f"Posting to Facebook Page {self.config.page_id}")
        result = self._make_request('POST', endpoint, params=params)

        if 'id' in result:
            logger.info(f"Successfully posted. Post ID: {result['id']}")
            return {
                "status": "success",
                "post_id": result['id'],
                "post_url": f"https://facebook.com/{result['id']}"
            }

        return result

    def get_page_insights(self, since: str = None, until: str = None,
                         metrics: List[str] = None) -> Dict[str, Any]:
        """
        Get page insights/analytics

        Args:
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            metrics: List of metrics to retrieve

        Returns:
            Analytics data
        """
        if not metrics:
            metrics = [
                'page_impressions',
                'page_engaged_users',
                'page_fan_adds',
                'page_actions_post_reactions_total'
            ]

        # Default to last 7 days
        if not until:
            until = datetime.now().strftime('%Y-%m-%d')
        if not since:
            since_date = datetime.now() - timedelta(days=7)
            since = since_date.strftime('%Y-%m-%d')

        params = {
            'metric': ','.join(metrics),
            'since': since,
            'until': until,
            'period': 'day'
        }

        endpoint = f"{self.config.page_id}/insights"
        result = self._make_request('GET', endpoint, params=params)

        if 'data' in result:
            # Parse insights into readable format
            insights = {}
            for item in result['data']:
                metric_name = item.get('name', 'unknown')
                values = item.get('values', [])
                total = sum(v.get('value', 0) for v in values)
                insights[metric_name] = {
                    'total': total,
                    'values': values
                }

            return {
                "status": "success",
                "period": {'since': since, 'until': until},
                "insights": insights
            }

        return result

    def get_ig_account_id(self) -> Optional[str]:
        """Get Instagram Business Account ID linked to the page"""
        if self.config.instagram_account_id:
            return self.config.instagram_account_id

        # Fetch from page
        result = self._make_request(
            'GET',
            f"{self.config.page_id}",
            params={'fields': 'instagram_business_account'}
        )

        if 'instagram_business_account' in result:
            return result['instagram_business_account']['id']

        return None

    def post_to_instagram(self, image_url: str, caption: str) -> Dict[str, Any]:
        """
        Post to Instagram Business Account

        Requires:
        - Instagram Business Account connected to Facebook Page
        - Image URL must be publicly accessible

        Args:
            image_url: Publicly accessible image URL
            caption: Post caption

        Returns:
            API response with media ID
        """
        ig_account_id = self.get_ig_account_id()

        if not ig_account_id:
            return {
                "error": "No Instagram Business Account linked to this page",
                "hint": "Set INSTAGRAM_BUSINESS_ACCOUNT_ID or ensure page is connected"
            }

        # Step 1: Create media container
        logger.info(f"Creating Instagram media container for account {ig_account_id}")
        create_endpoint = f"{ig_account_id}/media"
        create_params = {
            'image_url': image_url,
            'caption': caption
        }

        create_result = self._make_request('POST', create_endpoint, params=create_params)

        if 'error' in create_result:
            return create_result

        creation_id = create_result.get('id')
        if not creation_id:
            return {"error": "Failed to get creation ID", "response": create_result}

        # Step 2: Publish the container
        logger.info(f"Publishing Instagram media {creation_id}")
        publish_endpoint = f"{ig_account_id}/media_publish"
        publish_params = {'creation_id': creation_id}

        publish_result = self._make_request('POST', publish_endpoint, params=publish_params)

        if 'id' in publish_result:
            logger.info(f"Successfully posted to Instagram. Media ID: {publish_result['id']}")
            return {
                "status": "success",
                "media_id": publish_result['id'],
                "permalink": f"https://instagram.com/p/{publish_result.get('shortcode', '')}"
            }

        return publish_result

    def get_ig_insights(self, since: str = None, until: str = None) -> Dict[str, Any]:
        """Get Instagram Business Account insights"""
        ig_account_id = self.get_ig_account_id()

        if not ig_account_id:
            return {"error": "No Instagram Business Account linked"}

        # Default dates
        if not until:
            until = datetime.now().strftime('%Y-%m-%d')
        if not since:
            since_date = datetime.now() - timedelta(days=7)
            since = since_date.strftime('%Y-%m-%d')

        metrics = ['impressions', 'reach', 'profile_views', 'follower_count']

        params = {
            'metric': ','.join(metrics),
            'since': since,
            'until': until,
            'period': 'day'
        }

        endpoint = f"{ig_account_id}/insights"
        result = self._make_request('GET', endpoint, params=params)

        if 'data' in result:
            insights = {}
            for item in result['data']:
                metric_name = item.get('name', 'unknown')
                values = item.get('values', [])
                total = sum(v.get('value', 0) for v in values)
                insights[metric_name] = {
                    'total': total,
                    'values': values
                }

            return {
                "status": "success",
                "account_id": ig_account_id,
                "period": {'since': since, 'until': until},
                "insights": insights
            }

        return result


class SocialMCP:
    """
    Social Media MCP Server

    Provides unified interface for Facebook and Instagram operations
    with approval workflow integration.
    """

    def __init__(self):
        self.config = SocialConfig.from_env()
        self.api = FacebookGraphAPI(self.config)
        self.vault_path = Path(os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault'))

    def requires_approval(self, content: str, platform: str) -> bool:
        """
        Determine if post requires Human-in-the-Loop approval

        Per Company Handbook:
        - All social media posts require approval
        """
        return True  # All posts require approval

    def create_approval_request(self, platform: str, content: str,
                               metadata: Dict = None) -> str:
        """
        Create approval request file in Pending_Approval folder

        Returns:
            Request ID
        """
        request_id = f"SOCIAL_{platform.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        approval_file = self.vault_path / "Pending_Approval" / f"{request_id}.md"
        approval_file.parent.mkdir(parents=True, exist_ok=True)

        content_md = f"""---
type: approval_request
action: social_post
platform: {platform}
request_id: {request_id}
created: {datetime.now().isoformat()}
status: pending
---

# Social Media Post Approval Required

## Platform
{platform}

## Content
```
{content}
```

## Metadata
{json.dumps(metadata or {}, indent=2)}

## To Approve
Move this file to `/Approved/` folder.

## To Reject
Move this file to `/Rejected/` folder.

## Note
This post was generated by the AI Employee and requires human approval before publishing per Company Handbook v2.0.
"""

        approval_file.write_text(content_md, encoding='utf-8')
        logger.info(f"Created approval request: {approval_file}")

        return request_id

    def post_to_page(self, message: str, link: str = None,
                    image_url: str = None, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Post to Facebook Page with approval workflow

        Args:
            message: Post text
            link: Optional link
            image_url: Optional image URL
            auto_approve: Skip approval (testing only)

        Returns:
            Result dict with status
        """
        if not auto_approve and self.requires_approval(message, 'facebook'):
            request_id = self.create_approval_request(
                platform='facebook',
                content=message,
                metadata={'link': link, 'image_url': image_url}
            )
            return {
                "status": "pending_approval",
                "request_id": request_id,
                "message": "Post queued for approval. Check /Pending_Approval folder."
            }

        return self.api.post_to_page(message, link, image_url)

    def post_to_instagram(self, image_url: str, caption: str,
                         auto_approve: bool = False) -> Dict[str, Any]:
        """
        Post to Instagram with approval workflow

        Args:
            image_url: Publicly accessible image URL
            caption: Post caption
            auto_approve: Skip approval (testing only)

        Returns:
            Result dict with status
        """
        if not auto_approve and self.requires_approval(caption, 'instagram'):
            request_id = self.create_approval_request(
                platform='instagram',
                content=caption,
                metadata={'image_url': image_url}
            )
            return {
                "status": "pending_approval",
                "request_id": request_id,
                "message": "Post queued for approval. Check /Pending_Approval folder."
            }

        return self.api.post_to_instagram(image_url, caption)

    def get_page_insights(self, **kwargs) -> Dict[str, Any]:
        """Get Facebook Page insights"""
        return self.api.get_page_insights(**kwargs)

    def get_instagram_insights(self, **kwargs) -> Dict[str, Any]:
        """Get Instagram Business insights"""
        return self.api.get_ig_insights(**kwargs)

    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly social media summary"""
        since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        until = datetime.now().strftime('%Y-%m-%d')

        # Get Facebook insights
        fb_insights = self.api.get_page_insights(since=since, until=until)

        # Get Instagram insights
        ig_insights = self.api.get_ig_insights(since=since, until=until)

        report = {
            "period": {"since": since, "until": until},
            "generated_at": datetime.now().isoformat(),
            "facebook": fb_insights if 'error' not in fb_insights else None,
            "instagram": ig_insights if 'error' not in ig_insights else None
        }

        # Save to Briefings folder
        report_file = self.vault_path / "Briefings" / f"social_report_{datetime.now().strftime('%Y%m%d')}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        report_md = f"""---
type: social_media_report
date: {datetime.now().isoformat()}
period: {since} to {until}
---

# Social Media Weekly Report

**Period:** {since} to {until}

## Facebook Page Insights
{json.dumps(fb_insights.get('insights', {}), indent=2) if fb_insights and 'insights' in fb_insights else 'No data available'}

## Instagram Insights
{json.dumps(ig_insights.get('insights', {}), indent=2) if ig_insights and 'insights' in ig_insights else 'No data available'}

## Summary
Generated by AI Employee Social MCP
"""

        report_file.write_text(report_md, encoding='utf-8')
        logger.info(f"Generated social media report: {report_file}")

        return report


def main():
    """Run Social MCP Server"""
    import argparse

    parser = argparse.ArgumentParser(description='Social Media MCP Server')
    parser.add_argument('command',
                        choices=['test', 'post-facebook', 'post-instagram',
                                'insights', 'ig-insights', 'report'],
                        default='test',
                        nargs='?',
                        help='Command to run')
    parser.add_argument('--message', '-m', help='Post message content')
    parser.add_argument('--image-url', help='Image URL for Instagram posts')
    parser.add_argument('--link', help='Link to include in Facebook post')
    parser.add_argument('--auto-approve', action='store_true',
                        help='Skip approval workflow (testing only)')

    args = parser.parse_args()

    print("="*60)
    print("📱 SOCIAL MEDIA MCP SERVER - GOLD TIER")
    print("="*60)

    mcp = SocialMCP()

    if args.command == 'test':
        print("\n🔍 Testing Facebook Graph API connection...")
        result = mcp.api.test_connection()

        if result.get('status') == 'connected':
            print(f"✅ Connected successfully!")
            print(f"   Page: {result.get('page_name')}")
            print(f"   Page ID: {result.get('page_id')}")
            print(f"   API Version: {result.get('api_version')}")

            # Check Instagram
            ig_id = mcp.api.get_ig_account_id()
            if ig_id:
                print(f"   Instagram Account: {ig_id}")
            else:
                print(f"   Instagram Account: Not linked")
        else:
            print(f"❌ Connection failed: {result.get('error', result.get('message', 'Unknown'))}")
            print("\nConfiguration:")
            print(f"   FACEBOOK_PAGE_ID: {'✅ Set' if os.getenv('FACEBOOK_PAGE_ID') else '❌ Not set'}")
            print(f"   FACEBOOK_ACCESS_TOKEN: {'✅ Set' if os.getenv('FACEBOOK_ACCESS_TOKEN') else '❌ Not set'}")
            print(f"   INSTAGRAM_BUSINESS_ACCOUNT_ID: {'✅ Set' if os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID') else '❌ Not set'}")

    elif args.command == 'post-facebook':
        if not args.message:
            print("❌ --message required")
            return 1

        print(f"\n📝 Posting to Facebook...")
        result = mcp.post_to_page(
            message=args.message,
            link=args.link,
            auto_approve=args.auto_approve
        )

        if result.get('status') == 'pending_approval':
            print(f"⏳ {result['message']}")
            print(f"   Request ID: {result['request_id']}")
        elif result.get('status') == 'success':
            print(f"✅ Posted successfully!")
            print(f"   Post ID: {result.get('post_id')}")
            print(f"   URL: {result.get('post_url')}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    elif args.command == 'post-instagram':
        if not args.message or not args.image_url:
            print("❌ --message and --image-url required")
            return 1

        print(f"\n📸 Posting to Instagram...")
        result = mcp.post_to_instagram(
            image_url=args.image_url,
            caption=args.message,
            auto_approve=args.auto_approve
        )

        if result.get('status') == 'pending_approval':
            print(f"⏳ {result['message']}")
            print(f"   Request ID: {result['request_id']}")
        elif result.get('status') == 'success':
            print(f"✅ Posted successfully!")
            print(f"   Media ID: {result.get('media_id')}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    elif args.command == 'insights':
        print("\n📊 Getting Facebook Page insights...")
        result = mcp.get_page_insights()

        if result.get('status') == 'success':
            print(f"\nPeriod: {result['period']['since']} to {result['period']['until']}")
            for metric, data in result.get('insights', {}).items():
                print(f"   {metric}: {data['total']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    elif args.command == 'ig-insights':
        print("\n📊 Getting Instagram insights...")
        result = mcp.get_instagram_insights()

        if result.get('status') == 'success':
            print(f"\nPeriod: {result['period']['since']} to {result['period']['until']}")
            for metric, data in result.get('insights', {}).items():
                print(f"   {metric}: {data['total']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    elif args.command == 'report':
        print("\n📈 Generating weekly social media report...")
        result = mcp.generate_weekly_report()
        print(f"✅ Report generated!")

    print("\n" + "="*60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
