# Gmail

Butler can **read** your mailbox: list, search, count and open emails. If you switch it on, it can also **reply, send and save drafts**, and every reply or new email waits for your **Approve**. It never deletes, archives or labels anything.

## What you can ask

```
How many unread mails do I have in Promotions?
Show my latest 10 mails in Updates from LinkedIn
Any unread mail with attachments since 2026/10/01?
What did I send to priya@example.com last month?
Open a mail from Amazon                    ← shows a picker, then the full email
```

Tabs and folders it understands: **primary** (the default), promotions, social, updates, forums, purchases, inbox, starred, snoozed, sent, drafts, important, spam, trash, and all.

## Replying and sending (optional)

Off by default. To turn it on:

1. Open the web UI → **Integrations** → **Gmail** card, and switch on **Allow replying & sending**. (Or set `GMAIL_ALLOW_SEND=true` in `.env` as the default.)
2. The card then says *"Gmail hasn't granted permission to send yet."* Click **Reconnect**, or run `python -m butler gmail-login`, and allow **"Send email on your behalf" / manage drafts** in the Google window.

Then you can ask:

```
Reply to Priya's dinner email: yes, Friday at 8 works
Reply all to the project thread saying I'll send the slides tonight
Send an email to ravi@example.com saying the report is ready
Draft a reply to the landlord asking to move the visit to Sunday   ← saved to Drafts, never sent
```

| Tool | Does | Asks first? |
|---|---|---|
| `reply_to_email` | Reply (or reply-all) in the same conversation | ✅ The card shows To, Cc, Subject and the full text |
| `send_email` | Send a new email | ✅ Same |
| `create_draft` | Save a new email or a reply to **Drafts**; you send it from Gmail | No; nothing is sent |

**Safety:**
- **Nothing is sent without your Approve.** Rejecting, or sending a new message instead, sends nothing.
- **Replies thread properly** (`Re:`, `In-Reply-To`, `References`, same Gmail thread) and go to the sender, or the Reply-To address if set. Reply-all adds the others. Your own address is never included.
- **Butler only writes to addresses you gave it** or that it found in your mail; it never guesses.
- **On Telegram,** only `TELEGRAM_OWNER_ID` can approve a send.
- **Switching it off** takes effect immediately, in the web UI and Telegram. The extra Google permission stays granted until you revoke it at [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

## One-time setup: create your Google OAuth client

Google only lets apps read Gmail if they're registered. Since Butler runs on your machine, you register *your own* copy. It's free and nobody else can use it.

### 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and sign in with the Google account whose mail you want to read.
2. Click the project picker (top-left) → **New project**. Name it, for example, `butler`, and click **Create**.

### 2. Enable the Gmail API

1. Open **APIs & Services → Library**.
2. Search for **Gmail API**, open it, and click **Enable**.

### 3. Set up the consent screen

1. Open **APIs & Services → OAuth consent screen** (shown as **Google Auth Platform** in newer consoles) and click **Get started**.
2. **App name:** `Butler`. **User support email:** your email.
3. **Audience:** choose **External**.
4. **Contact information:** your email. Then finish the wizard.
5. Under **Audience → Test users**, click **Add users** and add **your own Gmail address**.

### 4. Create the OAuth client

1. Open **APIs & Services → Credentials** (or **Clients** in Google Auth Platform) → **Create credentials → OAuth client ID**.
2. **Application type:** **Desktop app**. Name: `Butler`.
3. Click **Create**, then **Download JSON**.
4. Save the downloaded file as:

   ```
   secrets/google_client_secret.json
   ```

   This is inside your Butler folder. It's git-ignored.

### 5. Log in

```bash
python -m butler gmail-login
```

A browser opens:

1. Pick your Google account.
2. You'll see **"Google hasn't verified this app."** That's expected: it's *your* app. Click **Continue**.
3. Allow **"View your email messages and settings"**.

The terminal prints `Gmail connected: you@gmail.com`, and the token is saved in `secrets/gmail_token.json`.

You can also click **Connect** next to Gmail on the web UI's **Integrations** page. The browser window opens on the machine running Butler.

## Good to know

- **The login lasts about 7 days.** While your Google app is in **Testing** mode, Google expires the login after about 7 days. When Butler says Gmail failed with `invalid_grant`, run `python -m butler gmail-login` again. To avoid this, open the consent screen settings and click **Publish app**. You'll still see the "unverified" warning when logging in, but the login won't expire weekly.
- **Disconnecting:** delete `secrets/gmail_token.json`. To revoke access completely, go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions) and remove **Butler**.
- **Quick reader without AI:** `python -m butler gmail updates --from linkedin --unread -n 10` prints mail straight from Gmail, without using the model.
- **Permissions:** reading uses `gmail.readonly`; replying, sending and drafts add `gmail.compose`, which is only requested once sending is switched on.
- **Where the code lives:** [`butler/integrations/gmail/`](../../butler/integrations/gmail/): `compose.py` builds replies, `settings.py` holds the switch, and `tools.py` has the read and write tools.
