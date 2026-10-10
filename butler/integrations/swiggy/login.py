"""Log in to Swiggy (phone + OTP in the browser) and save the token.

Run from the project root:
    python -m butler swiggy-login

One login covers every Swiggy service (Food, Instamart, Dineout).
Tokens last 5 days; run this again when the agent says login is required.
"""

import asyncio

from .client import get_swiggy_tools
from .config import SERVERS
from .tools import services_of, smoke_test


async def main():
    tools = await get_swiggy_tools(interactive=True)

    print(f"\nLogged in. {len(tools)} Swiggy tools available:")
    for service in SERVERS:
        names = [t.name for t in tools if t.name.startswith(service + "_")]
        print(f"\n  {service} ({len(names)})")
        for name in names:
            print("   -", name)

    missing = set(SERVERS) - services_of(tools)
    if missing:
        print(f"\nWARNING: no tools from: {', '.join(sorted(missing))}")

    print("\nYour saved addresses:")
    print(await smoke_test(tools))


if __name__ == "__main__":
    asyncio.run(main())
