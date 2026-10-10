# Terminal

The quickest way to talk to Butler, with no browser or bot to set up.

## Chat

```bash
python -m butler chat
```

```
Chat with your assistant (type 'exit' to quit)

You: How many unread mails in Social?
AI: You have 5,965 unread emails in your Social category.

You: Open a mail from primary

Which email do you want to open?
   1. ● DSP Mutual Fund                 DSP Monthly Portfolios: Update for You
   2.   Turing                          Reminder to update your interest…
   0. Cancel
Pick a number: 1
AI: Here are the details of the selected email: …
```

- **Email picker:** type the number of the email, or `0` to cancel. The dot (●) marks unread mail.
- **Approvals:** Butler prints the action and its details and asks `Approve? (y/n)`.
- **Leaving:** type `exit` or `quit`.

The conversation lasts for the session and is forgotten when you quit.

## Connect accounts

```bash
python -m butler gmail-login     # Google login in the browser
python -m butler swiggy-login    # phone number + OTP in the browser
```

## Quick Gmail reader (no AI)

Prints mail straight from Gmail. It uses no OpenAI calls, so it's handy for scripts:

```bash
python -m butler gmail                                  # latest 5 in Primary
python -m butler gmail updates --from linkedin -n 10    # 10 LinkedIn mails in Updates
python -m butler gmail primary --unread --after 2026/10/01
python -m butler gmail sent --to someone@example.com
python -m butler gmail starred --attachment
```

| Option | Meaning |
|---|---|
| `category` | primary (the default), promotions, social, updates, forums, purchases, inbox, starred, snoozed, sent, drafts, important, spam, trash, all |
| `-n`, `--limit` | How many emails to show (default 5) |
| `--from`, `--to`, `--subject` | Filter by sender, recipient, or subject |
| `--text` | Free-text search |
| `--unread` | Unread mail only |
| `--attachment` | Mail with attachments only |
| `--after`, `--before` | Date range, `YYYY/MM/DD` |

## All commands

```bash
python -m butler web | telegram | chat | gmail-login | swiggy-login | gmail
```

After `pip install -e .`, the shorter `butler <command>` works too.
