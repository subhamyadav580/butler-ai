import os

from butler.config import SECRETS_DIR

# Which Swiggy services to load. Fewer services = fewer tools for the LLM to
# choose from, which helps smaller models pick the right one.
SWIGGY_SERVICES = {
    s.strip().lower()
    for s in os.getenv("SWIGGY_SERVICES", "food,instamart,dineout").split(",")
    if s.strip()
}

# Swiggy's MCP servers. Tool names get the service as a prefix
# (food_get_addresses, instamart_get_addresses, …) because several tool
# names exist on more than one server.
ALL_SERVERS = {
    "food": "https://mcp.swiggy.com/food",            # restaurant delivery
    "instamart": "https://mcp.swiggy.com/im",         # groceries & essentials
    "dineout": "https://mcp.swiggy.com/dineout",      # table reservations
}

SERVERS = {name: url for name, url in ALL_SERVERS.items() if name in SWIGGY_SERVICES}

# One login covers every server (the token is issued for https://mcp.swiggy.com/)
AUTH_SERVER_URL = ALL_SERVERS["food"]

# Tools we never give the LLM:
# - report_error files a bug report with Swiggy's MCP team
# - render_restaurants_dineout only draws a widget, which Butler doesn't have
EXCLUDED_TOOLS = {
    "food_report_error",
    "instamart_report_error",
    "dineout_report_error",
    "dineout_render_restaurants_dineout",
}

# Holds the OAuth access token and the dynamically registered client
TOKEN_FILE = str(SECRETS_DIR / "swiggy_token.json")

# Swiggy allows http://localhost redirects for development without approval
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

CLIENT_NAME = "Butler"
SCOPES = "mcp:tools"

LOGIN_COMMAND = "python -m butler swiggy-login"
