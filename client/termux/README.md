# Secure MCP Server — Termux Client

A security-focused MCP client for Android Termux. It connects to a remote MCP server over HTTPS, authenticates through OAuth 2.0, and integrates an AI provider through a modular provider architecture.

> **Status:** Development / Experimental

## Features

- Connects to an MCP server using Streamable HTTP.
- HTTPS with certificate verification enabled.
- OAuth 2.0 authorization flow.
- Persistent OAuth token storage.
- Modular AI provider architecture.
- OpenRouter provider integration.
- Configurable server URL, CA certificate, provider, and model.
- Automated tests for configuration and orchestration.

## Project Structure

    client/termux/
    ├── .env.example
    ├── .gitignore
    ├── README.md
    ├── client.py
    ├── config.py
    ├── oauth_callback.py
    ├── oauth_storage.py
    ├── requirements.txt
    ├── agent/
    │   ├── __init__.py
    │   └── orchestrator.py
    ├── providers/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── factory.py
    │   └── openrouter_provider.py
    └── tests/
        ├── test_config.py
        └── test_orchestrator.py

## Requirements

- Android with Termux.
- Python 3.14 or a compatible Python environment.
- Network access to the MCP server.
- An MCP server configured for HTTPS and OAuth.
- An OpenRouter API key if using the OpenRouter provider.

## Installation

Clone the repository:

    git clone https://github.com/Zer-security/secure-mcp-server.git
    cd secure-mcp-server/client/termux

Create a virtual environment:

    python -m venv venv
    source venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

## Configuration

Create a local environment file:

    cp .env.example .env

Edit `.env`:

    MCP_SERVER_URL=https://YOUR_SERVER_HOST:8000/mcp
    MCP_SERVER_CA_CERT=
    AI_PROVIDER=openrouter
    AI_MODEL=openrouter/free
    OPENROUTER_API_KEY=

Replace the server placeholder with the actual MCP server endpoint.

### TLS Certificate Configuration

TLS certificate verification is enabled by default.

For a server using a private or self-signed CA certificate, provide the trusted certificate path:

    MCP_SERVER_CA_CERT=/path/to/mcp-server.crt

For a server using a certificate trusted by the system certificate store, leave `MCP_SERVER_CA_CERT` empty.

**Important:** Never disable TLS verification in production. Do not commit private keys, machine-specific certificates, or local credentials.

### OpenRouter Configuration

Set your API key in `.env`:

    OPENROUTER_API_KEY=your_api_key

Never publish `.env` or expose API keys in source code, logs, screenshots, or commits.

## Running the Client

Start the client:

    python client.py

The client connects to the configured MCP endpoint and uses the OAuth authorization flow when required.

## Testing

Run the available tests:

    python -m pytest -q tests/test_config.py tests/test_orchestrator.py

On the tested Termux environment, the following preload workaround was required:

    LD_PRELOAD="$PREFIX/lib/libpython3.14.so" ./venv/bin/python -m pytest -q tests/test_config.py tests/test_orchestrator.py

**Recorded test result:** 11 passed in 1.77 seconds.

The preload requirement may differ across Termux and Python versions.

## Security Notes

- TLS certificate verification remains enabled.
- OAuth tokens are stored locally and must not be committed.
- API keys must be supplied through environment variables.
- Private certificates and keys must remain outside the public repository.
- Use only MCP servers you are authorized to access.
- This project is under active development and should be evaluated before production use.

## Current Limitations

- The client currently includes an OpenRouter provider implementation.
- Other AI providers require their own provider implementation.
- Server availability and OAuth configuration are external requirements.
- End-to-end AI-to-MCP-to-AI operation should be verified in the target environment.

## License

See the repository's root `LICENSE` file.

## Repository

[Secure MCP Server](https://github.com/Zer-security/secure-mcp-server)
