from butler.config import SWIGGY_TOKEN_FILE

SERVERS = {
    "food": "https://mcp.swiggy.com/food",
}

# Holds the OAuth access token and the dynamically registered client
TOKEN_FILE = str(SWIGGY_TOKEN_FILE)

# Swiggy allows http://localhost redirects for development without approval
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

CLIENT_NAME = "Butler"
SCOPES = "mcp:tools"

LOGIN_COMMAND = "python -m butler swiggy-login"
