from butler.config import SECRETS_DIR

# Zepto's official MCP server: https://github.com/zeptonow/mcp
SERVER_URL = "https://mcp.zepto.co.in/mcp"

# Tool names get "zepto_" in front (zepto_search_products, …) so they can't
# clash with Swiggy Instamart's tools
SERVER_NAME = "zepto"

# Holds the OAuth token and the dynamically registered client
TOKEN_FILE = SECRETS_DIR / "zepto_token.json"

# Login redirect: http://localhost:<port>/callback (Swiggy uses 8765)
REDIRECT_PORT = 8766

LOGIN_COMMAND = "python -m butler zepto-login"
