"""Log in to Swiggy (phone + OTP in the browser) and save the token.

Run from the project root:
    python -m butler swiggy-login

Tokens last 5 days; run this again when the agent says login is required.
"""

import asyncio

from .client import get_swiggy_tools


async def main():
    tools = await get_swiggy_tools(interactive=True)
    print(f"\nLogged in. {len(tools)} Swiggy tools available:")
    for tool in tools:
        print(" -", tool.name)

    # Smoke test: the first call every Swiggy integration should make
    get_addresses = next(t for t in tools if t.name == "get_addresses")
    print("\nYour saved addresses:")
    print(await get_addresses.ainvoke({}))


if __name__ == "__main__":
    asyncio.run(main())
