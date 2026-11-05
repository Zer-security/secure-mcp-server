import asyncio
import os
import webbrowser

import httpx
from mcp import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata

from oauth_callback import OAuthCallbackServer
from oauth_storage import FileTokenStorage


from ..config import MCP_SERVER_URL, MCP_SERVER_CA_CERT
REDIRECT_URI = "http://127.0.0.1:8765/callback"


async def main():
    callback = OAuthCallbackServer(host="127.0.0.1", port=8765)
    await callback.start()

    async def redirect_handler(authorization_url: str) -> None:
        print("\nBuka URL authorization berikut di browser:")
        print(authorization_url)
        webbrowser.open(authorization_url)

    async def callback_handler():
        return await callback.wait_for_result()

    metadata = OAuthClientMetadata(
        client_name="Termux MCP Client",
        redirect_uris=[REDIRECT_URI],
        token_endpoint_auth_method="none",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="mcp:read",
        application_type="native",
    )

    auth_provider = OAuthClientProvider(
        server_url=MCP_SERVER_URL,
        client_metadata=metadata,
        storage=FileTokenStorage(),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )

    try:
        async with httpx2.AsyncClient(
            auth=auth_provider,
            verify=MCP_SERVER_CA_CERT,
        ) as http_client:
            async with Client(
                streamable_http_client(
                    MCP_SERVER_URL,
                    http_client=http_client,
                )
            ) as client:
                    print("Terhubung ke MCP Server Kali!")

                    tools = await client.list_tools()
                    print("Tools:", [tool.name for tool in tools.tools])

                    result = await client.call_tool(
                        "network_interfaces",
                        {},
                    )

                    print("NETWORK INTERFACES:")
                    print(result)
    finally:
        await callback.stop()


if __name__ == "__main__":
    os.environ["LD_PRELOAD"] = os.path.join(
        os.environ["PREFIX"],
        "lib/libpython3.14.so",
    )
    asyncio.run(main())
