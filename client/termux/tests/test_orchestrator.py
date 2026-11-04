from client.termux.agent.orchestrator import parse_tool_calls, validate_tool_call


def test_parse_tool_calls():
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "network_interfaces",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            }
        ]
    }

    result = parse_tool_calls(response)

    assert len(result) == 1
    assert result[0]["id"] == "call_1"
    assert result[0]["name"] == "network_interfaces"
    assert result[0]["arguments"] == "{}"


def test_parse_tool_calls_empty():
    assert parse_tool_calls({"choices": []}) == []


def test_validate_tool_call_allowed():
    assert validate_tool_call(
        {"name": "network_interfaces"}
    ) is True


def test_validate_tool_call_rejected():
    import pytest

    with pytest.raises(ValueError, match="Tool tidak diizinkan"):
        validate_tool_call(
            {"name": "execute_shell"}
        )


def test_call_mcp_tool_rejects_non_object_arguments():
    import pytest
    from agent.orchestrator import call_mcp_tool

    with pytest.raises(ValueError, match="arguments tool harus berupa object JSON"):
        import asyncio
        asyncio.run(
            call_mcp_tool({
                "name": "network_interfaces",
                "arguments": "[]",
            })
        )


def test_extract_tool_text_normal():
    from agent.orchestrator import extract_tool_text
    from mcp_types import TextContent, CallToolResult

    result = CallToolResult(
        content=[TextContent(type="text", text="hasil normal")]
    )

    assert extract_tool_text(result) == "hasil normal"


def test_extract_tool_text_error():
    from agent.orchestrator import extract_tool_text
    from mcp_types import TextContent, CallToolResult

    result = CallToolResult(
        content=[TextContent(type="text", text="terjadi kesalahan")],
        isError=True,
    )

    assert extract_tool_text(result) == "MCP tool error: terjadi kesalahan"


def test_grounding_instruction_blocks_network_inference():
    from agent.orchestrator import GROUNDING_INSTRUCTION

    assert "Jangan menebak atau mengarang gateway" in GROUNDING_INSTRUCTION
    assert "status koneksi" in GROUNDING_INSTRUCTION
    assert "informasi tersebut tidak tersedia" in GROUNDING_INSTRUCTION
