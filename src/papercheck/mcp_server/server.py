"""FastMCP server for papercheck.

``main()`` builds the server and starts it. Importing this module has no side
effects: the blocking ``run()`` call happens only inside ``main()`` (or when the
module is executed directly). No tools are registered yet.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def main() -> None:
    """Build the papercheck FastMCP server and run it (blocking)."""
    mcp = FastMCP("papercheck")
    mcp.run()


if __name__ == "__main__":
    main()
