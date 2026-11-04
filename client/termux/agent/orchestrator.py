import asyncio
import os
import webbrowser
from contextlib import asynccontextmanager

import httpx
from ..config import MCP_SERVER_URL, MCP_SERVER_CA_CERT
from mcp import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata
from ..oauth_callback import OAuthCallbackServer
from ..oauth_storage import FileTokenStorage
from ..providers.factory import create_provider

GROUNDING_INSTRUCTION = """
Gunakan hanya fakta yang secara langsung didukung oleh hasil MCP atau informasi yang diberikan pengguna.
Jangan menganggap keberadaan interface atau alamat IP sebagai bukti bahwa interface aktif, terhubung, memiliki akses internet, menggunakan router tertentu, atau menerima DHCP.
Jangan menebak atau mengarang gateway, DHCP, status koneksi, akses internet, interface utama, atau fakta jaringan lain yang tidak diberikan.
Jika informasi yang diminta tidak tersedia dari hasil MCP, katakan bahwa informasi tersebut tidak tersedia.
"""


async def ask_ai(prompt: str) -> str:
    """Mengirim prompt ke AI provider yang dikonfigurasi."""
    provider = create_provider()
    return await provider.generate(prompt)


@asynccontextmanager
async def mcp_client():
    """Membuka koneksi MCP dengan TLS CA dan OAuth yang dikonfigurasi."""
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
        redirect_uris=["http://127.0.0.1:8765/callback"],
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
                yield client
    finally:
        await callback.stop()


async def get_mcp_tools():
    """Mengambil daftar tools dari MCP Server Kali."""
    async with mcp_client() as client:
        result = await client.list_tools()
        return [tool.name for tool in result.tools]


async def get_mcp_tool_descriptions():
    """Mengambil metadata tools MCP untuk diberikan ke AI."""
    async with mcp_client() as client:
        result = await client.list_tools()

        tools = []

        for tool in result.tools:
            if tool.name not in ALLOWED_TOOLS:
                continue

            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema,
            })

        return tools

def parse_tool_calls(response: dict) -> list[dict]:
    """Mengambil tool call dari respons AI."""
    choices = response.get("choices", [])

    if not choices:
        return []

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    parsed = []

    for call in tool_calls:
        function = call.get("function", {})

        parsed.append({
            "id": call.get("id"),
            "name": function.get("name"),
            "arguments": function.get("arguments", "{}"),
        })

    return parsed

ALLOWED_TOOLS = {
    "kali_info",
    "system_status",
    "disk_status",
    "memory_status",
    "network_status",
    "network_interfaces",
    "read_text_file",
}


def validate_tool_call(tool_call: dict) -> bool:
    """Memastikan tool call hanya menggunakan tool yang diizinkan."""
    name = tool_call.get("name")

    if name not in ALLOWED_TOOLS:
        raise ValueError(f"Tool tidak diizinkan: {name}")

    return True

async def call_mcp_tool(tool_call: dict):
    """Memanggil satu tool MCP yang sudah divalidasi."""
    validate_tool_call(tool_call)

    import json

    name = tool_call["name"]
    arguments = json.loads(tool_call.get("arguments", "{}"))

    if not isinstance(arguments, dict):
        raise ValueError("arguments tool harus berupa object JSON")

    async with mcp_client() as client:
        return await client.call_tool(name, arguments)

def extract_tool_text(result) -> str:
    """Mengambil teks dari hasil CallToolResult MCP."""
    from mcp_types import TextContent

    texts = []

    for item in result.content:
        if isinstance(item, TextContent):
            texts.append(item.text)

    text = "\n".join(texts)

    if result.is_error:
        return f"MCP tool error: {text}" if text else "MCP tool error."

    return text


async def execute_tool_call(tool_call: dict):
    """Validasi dan jalankan satu MCP tool call."""
    validate_tool_call(tool_call)
    return await call_mcp_tool(tool_call)

async def run_agent(prompt: str):
    """Menjalankan alur AI -> MCP -> AI."""
    provider = create_provider()
    tools = await get_mcp_tool_descriptions()

    response = await provider.generate_with_tools(GROUNDING_INSTRUCTION + "\n\nPermintaan pengguna:\n" + prompt, tools)
    tool_calls = parse_tool_calls(response)

    if not tool_calls:
        return response["choices"][0]["message"].get("content", "")

    results = []

    for tool_call in tool_calls:
        results.append(
            await execute_tool_call(tool_call)
        )

    final_response = await generate_final_response(
        prompt,
        response,
        results,
    )

    return final_response

async def generate_final_response(prompt: str, response: dict, results: list):
    """Mengirim hasil MCP kembali ke AI untuk jawaban akhir."""
    provider = create_provider()

    tool_calls = parse_tool_calls(response)

    messages = [
        {
            "role": "system",
            "content": GROUNDING_INSTRUCTION,
        },
        {
            "role": "user",
            "content": prompt,
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": call["arguments"],
                    },
                }
                for call in tool_calls
            ],
        },
    ]

    for call, result in zip(tool_calls, results):
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": extract_tool_text(result),
        })

    result = await provider.generate_with_messages(messages)
    return result["choices"][0]["message"].get("content", "")
