import base64
import html


def get_header(headers, name):
    return next(
        (
            h["value"]
            for h in headers
            if h["name"].lower() == name.lower()
        ),
        ""
    )


def parse_summary(msg):
    """Turn a Gmail API message into a flat dict."""
    headers = msg["payload"].get("headers", [])
    labels = msg.get("labelIds", [])

    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "from": get_header(headers, "From"),
        "to": get_header(headers, "To"),
        "subject": get_header(headers, "Subject"),
        "date": get_header(headers, "Date"),
        # Gmail returns snippets HTML-escaped (&quot;, &#39;, ...)
        "snippet": html.unescape(msg.get("snippet", "")),
        "labels": labels,
        "unread": "UNREAD" in labels,
    }


def extract_body(payload):
    """Return the text/plain body, walking nested multipart parts."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode(
                "utf-8", errors="replace"
            )

    for part in payload.get("parts", []):
        body = extract_body(part)
        if body:
            return body

    return ""
