"""Log in to Zepto (phone + OTP in the browser) and save the token.

Run from the project root:
    python -m butler zepto-login
"""

import asyncio

from .client import get_zepto_tools
from .tools import EXCLUDED_TOOLS, approval_question, needs_approval


async def main():
    tools = [t for t in await get_zepto_tools(interactive=True) if t.name not in EXCLUDED_TOOLS]
    print(f"\nLogged in. {len(tools)} Zepto tools available:")
    for tool in tools:
        note = f"   ← asks first: {approval_question(tool)}" if needs_approval(tool) else ""
        print(f"   - {tool.name}{note}")


if __name__ == "__main__":
    asyncio.run(main())
