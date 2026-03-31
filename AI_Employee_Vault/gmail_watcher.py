#!/usr/bin/env python3
"""
Gmail Watcher for AI Employee
=============================
A complete Gmail monitoring system using Gmail API with OAuth2 authentication.

Features:
- OAuth2 authentication with automatic token refresh
- Read unread emails from inbox
- Display email details (subject, sender, body)
- Optionally mark emails as read
- Automatic token persistence

Setup Instructions:
-------------------
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and click "Enable"
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure OAuth consent screen:
     * Select "External" (or "Internal" for Workspace)
     * Fill in app name, user support email, developer contact
     * Add scope: https://www.googleapis.com/auth/gmail.readonly
     * Add scope: https://www.googleapis.com/auth/gmail.modify
     * Add your Gmail as a test user
   - Application type: "Desktop app"
   - Name: "AI Employee Gmail Watcher"
   - Download the JSON and save as 'credentials.json' in project root
5. Install dependencies:
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
6. Run this script - browser will open for authentication
7. token.json will be created automatically after first login

Required OAuth Scopes:
- https://www.googleapis.com/auth/gmail.readonly (Read emails)
- https://www.googleapis.com/auth/gmail.modify (Mark as read, labels)

Note:
- token.json stores your authentication (keep it secure)
- credentials.json is your OAuth client config (keep it secure, don't commit to git)
"""

import os
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Fix Windows console encoding issues
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('GmailWatcher')

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',      # Read emails
    'https://www.googleapis.com/auth/gmail.modify'         # Mark as read, modify labels
]


class GmailWatcher:
    """
    A complete Gmail watcher with OAuth2 authentication.

    Handles authentication, token refresh, reading emails, and marking them as read.
    """

    def __init__(
        self,
        credentials_path: str = './credentials.json',
        token_path: str = './token.json',
        port: int = 8080
    ):
        """
        Initialize the Gmail Watcher.

        Args:
            credentials_path: Path to credentials.json from Google Cloud Console
            token_path: Path where token.json will be saved/loaded
            port: Local port for OAuth callback (default: 8080)
        """
        self.credentials_path = Path(credentials_path).resolve()
        self.token_path = Path(token_path).resolve()
        self.port = port
        self.service = None
        self.user_email = None

        # Validate credentials file exists
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                f"Please download credentials.json from Google Cloud Console\n"
                f"and place it at: {self.credentials_path}"
            )

        # Authenticate on initialization
        self._authenticate()

    def _authenticate(self) -> None:
        """
        Authenticate with Gmail API using OAuth2.

        Flow:
        1. Try to load existing token from token.json
        2. If valid, use it
        3. If expired but has refresh token, refresh it
        4. If no valid token, run OAuth flow and save new token
        """
        creds = None

        # Step 1: Try to load existing token
        if self.token_path.exists():
            logger.info(f"Loading existing token from: {self.token_path}")
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path),
                    SCOPES
                )
                logger.info("Token loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")

        # Step 2: Check if credentials are valid
        if creds and creds.valid:
            logger.info("Token is valid")
            self.service = build('gmail', 'v1', credentials=creds)
            self._get_user_info()
            return

        # Step 3: Token expired - try to refresh
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, attempting refresh...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
                self._save_token(creds)
                self.service = build('gmail', 'v1', credentials=creds)
                self._get_user_info()
                return
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                # Continue to re-authentication

        # Step 4: No valid token - run OAuth flow
        logger.info("No valid token found. Starting OAuth flow...")
        logger.info(f"A browser window will open. Please authenticate with Google.")

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                SCOPES
            )

            # Run local server on specified port
            creds = flow.run_local_server(
                port=self.port,
                access_type='offline',      # Request refresh token
                prompt='consent'              # Force consent screen for refresh token
            )

            logger.info("OAuth authentication successful")
            self._save_token(creds)
            self.service = build('gmail', 'v1', credentials=creds)
            self._get_user_info()

        except Exception as e:
            raise RuntimeError(f"OAuth authentication failed: {e}")

    def _save_token(self, creds: Credentials) -> None:
        """
        Save credentials to token.json for future use.

        Args:
            creds: Credentials object to save
        """
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }

        try:
            with open(self.token_path, 'w') as token_file:
                json.dump(token_data, token_file, indent=2)
            logger.info(f"Token saved to: {self.token_path}")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def _get_user_info(self) -> None:
        """Get and store the authenticated user's email address."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile.get('emailAddress', 'Unknown')
            logger.info(f"Authenticated as: {self.user_email}")
        except HttpError as e:
            logger.warning(f"Could not retrieve user profile: {e}")
            self.user_email = 'Unknown'

    def fetch_unread_emails(
        self,
        max_results: int = 10,
        query: str = 'is:unread',
        include_body: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail inbox.

        Args:
            max_results: Maximum number of emails to fetch (default: 10)
            query: Gmail search query (default: 'is:unread')
            include_body: Whether to fetch full message body (default: True)

        Returns:
            List of email dictionaries with subject, sender, body, etc.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call _authenticate() first.")

        emails = []

        try:
            # Search for messages
            logger.info(f"Searching for emails with query: '{query}'")
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} messages")

            for msg_meta in messages:
                msg_id = msg_meta['id']
                email_data = self._get_email_details(msg_id, include_body)
                if email_data:
                    emails.append(email_data)

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise

        return emails

    def _get_email_details(
        self,
        message_id: str,
        include_body: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific email.

        Args:
            message_id: Gmail message ID
            include_body: Whether to include the message body

        Returns:
            Dictionary with email details or None if failed
        """
        try:
            # Fetch full message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full' if include_body else 'metadata'
            ).execute()

            # Extract headers
            headers = {}
            payload = message.get('payload', {})
            header_list = payload.get('headers', [])

            for header in header_list:
                headers[header['name'].lower()] = header['value']

            # Get subject, sender, date
            subject = headers.get('subject', 'No Subject')
            sender = headers.get('from', 'Unknown')
            date = headers.get('date', 'Unknown')
            to = headers.get('to', 'Unknown')

            # Extract body
            body = ''
            if include_body:
                body = self._extract_body(payload)
                # Limit body length for display
                if len(body) > 5000:
                    body = body[:5000] + '\n\n... [truncated]'

            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': subject,
                'sender': sender,
                'recipient': to,
                'date': date,
                'snippet': message.get('snippet', ''),
                'body': body,
                'labels': message.get('labelIds', []),
                'internal_date': message.get('internalDate')
            }

            return email_data

        except HttpError as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    def _extract_body(self, payload: Dict) -> str:
        """
        Extract the text body from a Gmail message payload.

        Args:
            payload: Gmail API message payload

        Returns:
            Decoded message body as string
        """
        body = ''

        # Check if this part has a body
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            try:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            except Exception:
                pass

        # Check for multipart message
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')

                # Prefer plain text, but accept HTML if no plain text
                if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                    try:
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                        break  # Found plain text, we're done
                    except Exception:
                        continue

                elif mime_type == 'text/html' and not body and 'data' in part.get('body', {}):
                    try:
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                        # Strip HTML tags for cleaner display
                        body = self._strip_html(body)
                    except Exception:
                        continue

                # Recursively check nested parts
                elif 'parts' in part:
                    nested_body = self._extract_body(part)
                    if nested_body:
                        body = nested_body
                        if 'text/plain' in str(part.get('mimeType', '')):
                            break

        return body.strip()

    def _strip_html(self, html: str) -> str:
        """
        Simple HTML tag stripping for display purposes.

        Args:
            html: HTML string

        Returns:
            Plain text with HTML tags removed
        """
        import re
        # Remove script and style elements
        text = re.sub(r'<(script|style)[^>]*>[^<]*</\1>', '', html, flags=re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a specific email as read by removing the UNREAD label.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated")
            return False

        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked message {message_id} as read")
            return True
        except HttpError as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark a specific email as unread by adding the UNREAD label.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated")
            return False

        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked message {message_id} as unread")
            return True
        except HttpError as e:
            logger.error(f"Failed to mark message as unread: {e}")
            return False

    def print_email(self, email: Dict[str, Any], index: Optional[int] = None) -> None:
        """
        Pretty print an email to console.

        Args:
            email: Email dictionary from fetch_unread_emails
            index: Optional index number for display
        """
        prefix = f"[{index}] " if index is not None else ""
        separator = "=" * 80

        print(f"\n{separator}")
        print(f"{prefix}Subject: {email['subject']}")
        print(f"From: {email['sender']}")
        print(f"To: {email['recipient']}")
        print(f"Date: {email['date']}")
        print(f"Message ID: {email['id']}")
        print(f"Labels: {', '.join(email['labels'])}")
        print(f"-" * 80)

        if email['body']:
            print(f"Body:\n{email['body'][:2000]}")  # Limit output
            if len(email['body']) > 2000:
                print("\n... [truncated for display]")
        else:
            print(f"Snippet: {email['snippet']}")

        print(separator)

    def check_and_print_emails(
        self,
        max_results: int = 10,
        auto_mark_read: bool = False,
        query: str = 'is:unread'
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to fetch and print emails.

        Args:
            max_results: Maximum emails to fetch
            auto_mark_read: Whether to mark fetched emails as read
            query: Gmail search query

        Returns:
            List of fetched emails
        """
        emails = self.fetch_unread_emails(max_results=max_results, query=query)

        if not emails:
            print("\nNo unread emails found.")
            return []

        print(f"\n{'='*80}")
        print(f"Found {len(emails)} email(s)")
        print(f"{'='*80}")

        for i, email in enumerate(emails, 1):
            self.print_email(email, i)

            if auto_mark_read:
                self.mark_as_read(email['id'])

        return emails


def main():
    """Main entry point with command-line argument support."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Gmail Watcher - Monitor Gmail inbox',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  python gmail_watcher.py

  # Check 5 unread emails and mark them as read
  python gmail_watcher.py --max 5 --mark-read

  # Check all emails from a specific sender
  python gmail_watcher.py --query "from:example@gmail.com"

  # Use custom credentials and token paths
  python gmail_watcher.py --credentials /path/to/creds.json --token /path/to/token.json
        """
    )

    parser.add_argument(
        '--credentials',
        default='./credentials.json',
        help='Path to credentials.json (default: ./credentials.json)'
    )
    parser.add_argument(
        '--token',
        default='./token.json',
        help='Path to token.json (default: ./token.json)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='OAuth callback port (default: 8080)'
    )
    parser.add_argument(
        '--max',
        dest='max_results',
        type=int,
        default=10,
        help='Maximum emails to fetch (default: 10)'
    )
    parser.add_argument(
        '--query',
        default='is:unread',
        help='Gmail search query (default: "is:unread")'
    )
    parser.add_argument(
        '--mark-read',
        action='store_true',
        help='Mark fetched emails as read'
    )
    parser.add_argument(
        '--no-body',
        dest='include_body',
        action='store_false',
        default=True,
        help='Skip fetching full message body (faster)'
    )

    args = parser.parse_args()

    try:
        # Initialize the watcher
        watcher = GmailWatcher(
            credentials_path=args.credentials,
            token_path=args.token,
            port=args.port
        )

        # Fetch and display emails
        emails = watcher.fetch_unread_emails(
            max_results=args.max_results,
            query=args.query,
            include_body=args.include_body
        )

        if not emails:
            print(f"\nNo emails found matching query: '{args.query}'")
            return

        print(f"\n{'='*80}")
        print(f"Found {len(emails)} email(s) matching: '{args.query}'")
        print(f"{'='*80}")

        for i, email in enumerate(emails, 1):
            watcher.print_email(email, i)

            if args.mark_read:
                watcher.mark_as_read(email['id'])

        print(f"\n{'='*80}")
        print(f"Summary: Fetched {len(emails)} email(s)")
        if args.mark_read:
            print("All fetched emails were marked as read.")
        print(f"{'='*80}\n")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure you have:")
        print("1. Created a project in Google Cloud Console")
        print("2. Enabled the Gmail API")
        print("3. Downloaded credentials.json and placed it in the project root")
        print("\nSee the docstring at the top of this file for detailed setup instructions.")

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == '__main__':
    main()
