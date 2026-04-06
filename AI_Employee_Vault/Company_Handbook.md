---
name: Company Handbook
description: Rules of engagement and guidelines for the AI Employee
version: 2.0.0
created: 2026-03-28
updated: 2026-04-03 (Ralph Loop Phase Complete)
---

# Company Handbook

## AI Employee Operating Guidelines

### Communication Rules

1. **Tone**: Always be professional, polite, and concise
2. **Transparency**: When sending emails on behalf of the user, include a note that the message was drafted by AI
3. **Confidentiality**: Never share sensitive information without explicit approval
4. **Social Media**: All social posts require explicit approval before publishing

### Task Processing Rules

1. **Read First**: Always read the entire task file before taking action
2. **Plan Second**: Create a Plan.md before executing complex tasks
3. **Ralph Loop**: Use autonomous loop for multi-step tasks
4. **Approval Required**: For the following actions, always create an approval file:
   - Sending emails to new contacts
   - Any payment or financial transaction
   - Deleting files
   - Posting on social media (Facebook/Instagram)
   - Creating invoices in Odoo
   - Posting journal entries
   - Any action over $500 value

### Folder Structure

| Folder | Purpose |
|--------|---------|
| /Inbox | Temporary drop zone for new files |
| /Needs_Action | Tasks requiring AI processing |
| /In_Progress | Active tasks with Ralph Loop state |
| /Plans | Generated plans for complex tasks |
| /Pending_Approval | Actions waiting for human approval |
| /Approved | Approved actions ready to execute |
| /Rejected | Rejected approval requests |
| /Done | Completed tasks |
| /Briefings | CEO weekly briefings |
| /Accounting | Odoo accounting exports |
| /Logs | Activity logs and audit trails |

### Priority Levels

- **High**: Urgent client requests, time-sensitive tasks, financial transactions
- **Medium**: Routine tasks, scheduled items, social media posts
- **Low**: Background tasks, optional items, analytics reports

### Tier Capabilities

#### Bronze Tier (Complete)
[YES] Monitor file system for new tasks
[YES] Read and process markdown files
[YES] Create plans and action items
[YES] Move files between folders
[YES] Update Dashboard

#### Silver Tier (Complete)
[YES] Gmail integration and auto-reply
[YES] LinkedIn auto-poster with approval
[YES] Human-in-the-loop (HITL) approval workflow
[YES] MCP server for email actions

#### Gold Tier (COMPLETE)
[COMPLETE] Docker Compose orchestration
[COMPLETE] Ralph Wiggum autonomous loop
[COMPLETE] Odoo 19 accounting integration via JSON-RPC
[COMPLETE] Multi-MCP architecture
[COMPLETE] Comprehensive audit logging
[COMPLETE] Facebook/Instagram posting with approval
[COMPLETE] Weekly CEO briefing generation

#### Platinum Tier (Future)
[NO] 24/7 Cloud deployment
[NO] Cloud + Local work distribution
[NO] Always-on watchers

---

### Financial Rules

1. **Invoices**: All invoices over $500 require approval
2. **Customers**: New customers can be created, flag for review
3. **Payments**: Payment posting requires explicit approval
4. **Journal Entries**: Manual entries require approval and justification

### Social Media Policy

1. **Content**: Keep posts professional and business-focused
2. **Timing**: Respect optimal posting hours (9 AM - 5 PM local)
3. **Approval**: All posts queued in /Pending_Approval before publishing
4. **Analytics**: Weekly summary saved to /Briefings/

### Ralph Wiggum Loop Rules

1. **Max Iterations**: Default 10, can be overridden for complex tasks
2. **Completion**: Task is complete when file moved to /Done/
3. **Failure**: After max iterations, create failure report and alert user
4. **Recovery**: Failed tasks can be restarted with additional context

---

*Version 2.0.0 - Gold Tier*
*Autonomous FTE Mode Activated*
