"""Run the web UI server."""

import uvicorn

from butler.config import WEB_HOST, WEB_PASSWORD, WEB_PORT


def main():
    if WEB_HOST not in ("127.0.0.1", "localhost") and not WEB_PASSWORD:
        print(
            f"WARNING: serving on {WEB_HOST} without BUTLER_WEB_PASSWORD — anyone "
            "who can reach this address can use your connected accounts."
        )
    print(f"Butler web UI: http://{WEB_HOST}:{WEB_PORT}")
    uvicorn.run("butler.web.app:app", host=WEB_HOST, port=WEB_PORT)


if __name__ == "__main__":
    main()
