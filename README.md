# Secure MCP Server for Kali Linux

A security-focused Model Context Protocol (MCP) server for running a controlled set of read-only tools on Kali Linux and accessing them from an authorized client over HTTPS.

The project is designed around a simple principle: an AI client should not receive unrestricted access to the underlying operating system. MCP tools are explicitly registered, authenticated requests are scoped, and security-sensitive operations are kept outside the server's interface.

## Overview

This project provides a local MCP server that exposes selected system and security-related information through the MCP protocol.

The current implementation includes:

- OAuth 2.0 authentication
- PKCE with S256
- Scoped authorization using `mcp:read`
- Dynamic client registration
- Authorization-code and refresh-token flows
- Token revocation
- SQLite-backed OAuth state
- Request rate limiting
- DNS rebinding protection
- Host allowlisting
- Audit logging
- Recursive redaction of sensitive tool arguments
- Explicitly registered read-oriented tools
- HTTPS using an ECDSA P-256 certificate
- TLS certificate and private-key validation
- Non-root execution enforcement

The server does **not** expose a generic shell, command execution endpoint, or arbitrary code execution interface.

## Architecture

```text
┌──────────────────────────┐
│     Termux / MCP Client  │
└────────────┬─────────────┘
             │
             │ HTTPS
             │ OAuth 2.0 + PKCE
             ▼
┌──────────────────────────┐
│      Kali Linux Host     │
│                          │
│  Streamable HTTP MCP     │
│  Transport Security     │
│  OAuth Authorization     │
│  Rate Limiting           │
│  Audit Logging           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Allowlisted MCP Tools  │
│                          │
│   kali_info              │
│   system_status          │
│   disk_status             │
│   memory_status           │
│   network_status          │
│   network_interfaces      │
│   read_text_file          │
└──────────────────────────┘
```

## Security Model

The server follows a least-privilege approach.

An MCP client is not given access to the Kali shell. Instead, functionality is exposed through individual tools that are explicitly registered by the server.

This creates a smaller and more predictable interface between an AI client and the operating system.

### No Generic Shell Access

There is no generic shell, `exec`, or arbitrary command execution interface in the MCP server.

Tools must be explicitly implemented and registered before they can be called.

### Authentication and Authorization

The server uses OAuth 2.0 with a SQLite-backed authorization provider.

The current authorization model includes:

- Native public-client registration
- Authorization Code flow
- Refresh Token flow
- PKCE
- S256 code challenge method
- `mcp:read` scope
- Resource validation
- Authorization-code expiration
- Authorization-code one-time consumption
- Refresh-token hashing
- Token revocation

The server does not grant arbitrary scopes. The currently supported MCP scope is:

```text
mcp:read
```

### PKCE

PKCE is part of the authorization flow and the integration test suite verifies the S256 flow, including rejection of an incorrect code verifier.

PKCE is used to protect the authorization-code exchange for the public client model used by this project.

### Transport Security

The MCP server uses Streamable HTTP over HTTPS.

Transport security currently includes:

- DNS rebinding protection
- Explicit host allowlisting
- TLS certificate/key loading through Uvicorn
- ECDSA P-256 certificates
- Certificate SAN validation
- Certificate/private-key matching checks

The server's default application endpoint is:

```text
https://<MCP_PUBLIC_HOST>:8000/mcp
```

The default bind address is configurable through:

```text
MCP_HOST
```

and the default port is:

```text
MCP_PORT=8000
```

### Rate Limiting

Rate limiting is applied to the authentication and MCP endpoints:

```text
/register
/authorize
/token
/revoke
/mcp
```

The default configuration is:

```text
10 requests / 60 seconds
```

Both the limit and the time window can be configured through environment variables.

### Audit Logging

Tool activity is recorded through the MCP audit extension.

Audit records include information such as:

- UTC timestamp
- Tool name
- Sanitized arguments
- Execution status
- Tool result or error information

Sensitive argument values are recursively redacted before being passed to the audit logger.

Sensitive keys currently covered by the sanitizer include values such as:

```text
api_key
authorization
client_secret
password
refresh_token
secret
token
```

The sanitizer also handles nested dictionaries and sequences without modifying the original input.

## Available Tools

The current server registers the following read-oriented tools:

| Tool | Purpose |
|---|---|
| `kali_info` | Returns Kali/server information |
| `system_status` | Reports general system status |
| `disk_status` | Reports disk/storage information |
| `memory_status` | Reports memory information |
| `network_status` | Reports network status |
| `network_interfaces` | Lists network interface information |
| `read_text_file` | Reads permitted text-file content |

The tool interface is intentionally limited. New capabilities should be added as dedicated tools rather than by introducing generic command execution.

## Configuration

Configuration is controlled through environment variables.

Important settings include:

```text
MCP_HOST
MCP_PORT
MCP_PUBLIC_HOST
MCP_ISSUER
MCP_RESOURCE
JWT_ALGORITHM
OAUTH_DB_PATH
TLS_CERT_PATH
TLS_KEY_PATH
OAUTH_RATE_LIMIT
OAUTH_RATE_LIMIT_WINDOW_SECONDS
```

Secrets and private keys are kept outside the source code.

The project uses EdDSA/Ed25519 for JWT signing and ECDSA P-256 for the generated TLS certificate.

## TLS Certificate Management

TLS certificates are generated and validated by:

```text
scripts/generate_tls.py
```

The certificate generation process uses:

```text
ECDSA SECP256R1 / P-256
```

The certificate includes SAN entries for the configured LAN address and supported local names.

Before promotion, the certificate-management code validates:

1. Certificate/key compatibility
2. Required SAN entries
3. Certificate structure
4. Existing active-file backup
5. Rollback on promotion failure

The generated private key is written with restrictive filesystem permissions.

## Running the Server

The server is intended to run as a non-root user.

Start it from the project environment:

```bash
cd ~/mcp-kali
PYTHONPATH=. ./venv/bin/python server.py
```

The exact runtime configuration depends on the environment variables configured for the deployment.

## Testing

The project contains unit, security, OAuth, integration, transport, TLS, validation, and tool tests.

Current verified test result:

```text
118 passed
```

The full suite was executed with:

```bash
PYTHONPATH=. ./venv/bin/pytest -q
```

This result reflects the current repository state at the time of verification.

## Project Structure

A simplified view of the project:

```text
mcp-kali/
├── core/
│   ├── audit_extension.py
│   ├── audit_sanitizer.py
│   ├── oauth_provider.py
│   ├── oauth_routes.py
│   ├── security.py
│   └── ...
├── scripts/
│   └── generate_tls.py
├── tests/
│   ├── test_audit_extension.py
│   ├── test_audit_sanitizer.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_file_tools.py
│   ├── test_integration.py
│   ├── test_oauth_provider.py
│   ├── test_rate_limit.py
│   ├── test_security.py
│   ├── test_ssrf.py
│   ├── test_tls_generator.py
│   ├── test_tools.py
│   ├── test_transport_security.py
│   └── test_validation.py
├── config.py
├── server.py
├── LICENSE
└── README.md
```

## Security Boundaries

The current security boundaries are intentionally narrow:

```text
AI Client
   │
   │ OAuth + PKCE
   ▼
MCP HTTP Transport
   │
   │ Host validation
   │ Rate limiting
   ▼
Authorization Layer
   │
   │ mcp:read
   ▼
Registered MCP Tools
   │
   ▼
Read-only system information
```

The server should not be treated as a general-purpose remote administration interface.

Any future tool that interacts with the operating system should be reviewed against the project's least-privilege model before being exposed through MCP.

## Development Principles

The project follows these development principles:

- Least privilege
- Explicit allowlisting
- Secure defaults
- No generic shell execution
- No hardcoded secrets
- Input validation
- Authentication before protected operations
- Auditability
- Fail-safe behavior
- Reproducible testing
- Evidence-based security claims

Security changes should follow:

```text
Implement
   ↓
Test
   ↓
Verify
   ↓
Document
```

A feature should not be described as secure merely because it exists in the source code. The implementation and its relevant tests should be verified first.

## Current Status

The current implementation has a passing automated test suite:

```text
118 passed
```

Core authentication, authorization, transport-security controls, rate limiting, audit logging, TLS certificate handling, and read-oriented MCP tools are implemented and covered by the project's test suite.

The project is still under active development. Additional hardening and validation may be added as the architecture evolves.

## License

See [LICENSE](LICENSE) for the applicable license terms.
