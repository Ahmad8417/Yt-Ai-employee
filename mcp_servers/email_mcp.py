#!/usr/bin/env python3
"""
Email MCP Server for AI Employee - Silver Tier
Model Context Protocol server for sending emails via Gmail
"""

import os
import sys
import json
import smtplib
import logging
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EmailMCP')


class EmailMCP:
    """MCP Server for email operations"""

    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')

        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not set! Email sending will fail.")
            logger.warning("Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
            logger.warning("For Gmail, use an App Password (not your regular password).")

    def send_email(self, to: str, subject: str, body: str,
                   cc: str = None, bcc: str = None,
                   attachments: list = None, html: bool = False) -> dict:
        """Send an email"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = cc
            if bcc:
                msg['Bcc'] = bcc

            # Add body
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type))

            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={Path(attachment_path).name}'
                        )
                        msg.attach(part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)

            recipients = [to]
            if cc:
                recipients.extend(cc.split(','))
            if bcc:
                recipients.extend(bcc.split(','))

            server.sendmail(self.smtp_username, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {to}")

            return {
                'success': True,
                'message_id': f"{datetime.now().timestamp()}",
                'to': to,
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                'success': False,
                'error': str(e),
                'to': to,
                'subject': subject
            }

    def draft_email(self, to: str, subject: str, body: str,
                   cc: str = None, html: bool = False) -> dict:
        """Create an email draft (save to vault for review)"""
        vault_path = Path(os.getenv('AI_EMPLOYEE_VAULT', './AI_Employee_Vault'))
        drafts_folder = vault_path / 'Pending_Approval'
        drafts_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        draft_file = drafts_folder / f"EMAIL_DRAFT_{timestamp}.md"

        content = f"""---
type: email_draft
action: send_email
to: {to}
subject: {subject}
cc: {cc or ''}
html: {html}
created: {datetime.now().isoformat()}
status: pending_approval
---

# Email Draft

## Recipients
- **To:** {to}
- **Cc:** {cc or 'None'}
- **Bcc:** None

## Subject
{subject}

## Body
{body}

## Instructions
Review this email draft. To send:
1. Move this file to `/Approved` folder
2. The email will be sent automatically

To edit, modify the body above and re-approve.
"""

        draft_file.write_text(content, encoding='utf-8')

        return {
            'success': True,
            'draft_file': str(draft_file),
            'to': to,
            'subject': subject,
            'status': 'pending_approval'
        }


def process_mcp_request(request: dict) -> dict:
    """Process an MCP request"""
    mcp = EmailMCP()

    tool = request.get('tool')
    params = request.get('params', {})

    if tool == 'send_email':
        return mcp.send_email(
            to=params.get('to'),
            subject=params.get('subject'),
            body=params.get('body'),
            cc=params.get('cc'),
            bcc=params.get('bcc'),
            attachments=params.get('attachments'),
            html=params.get('html', False)
        )
    elif tool == 'draft_email':
        return mcp.draft_email(
            to=params.get('to'),
            subject=params.get('subject'),
            body=params.get('body'),
            cc=params.get('cc'),
            html=params.get('html', False)
        )
    else:
        return {
            'success': False,
            'error': f'Unknown tool: {tool}'
        }


def main():
    """Main entry point for MCP server"""
    print("Email MCP Server starting...", file=sys.stderr)
    logger.info("Email MCP Server started")

    # MCP servers communicate via stdin/stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = process_mcp_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError:
            print(json.dumps({
                'success': False,
                'error': 'Invalid JSON'
            }))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({
                'success': False,
                'error': str(e)
            }))
            sys.stdout.flush()


if __name__ == '__main__':
    main()
