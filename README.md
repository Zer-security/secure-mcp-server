# secure-mcp-server

**An MCP server for Kali Linux that deliberately has no shell access.**
Read-only, allowlisted tools behind OAuth 2.0 + PKCE, TLS, rate limiting, and audit logging.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Current release: `v1.0.0`**

---

## Why this project exists

Many MCP servers give an AI client a generic shell or `exec` endpoint. That makes a single prompt-injection or a leaked token potentially equivalent to broad control of the host.

`secure-mcp-server` takes the opposite approach: the client can only call a small set of **explicitly registered, read-oriented tools**. There is no shell, no command execution endpoint, and no arbitrary code execution interface.

Access is authenticated with OAuth 2.0 + PKCE and scoped to `mcp:read`.

## Features

- OAuth 2.0 Authorization Code and Refresh Token flows with PKCE (S256)
- Single MCP scope: `mcp:read`
- Dynamic public-client registration
- Token revocation
- SQLite-backed OAuth state
- Interactive consent step
- JWT signing with EdDSA (Ed25519)
- HTTPS with minimum TLS 1.2
- ECDSA P-256 certificate generation and validation
- DNS rebinding protection and explicit host allowlisting
- Rate limiting on `/register`, `/authorize`, `/token`, `/revoke`, and `/mcp`
- Audit logging with recursive redaction of sensitive arguments
- Refuses to run as root
- Read-only, explicitly registered MCP tools
- Test coverage for OAuth, transport security, TLS, rate limiting, validation, and tools

## Architecture

```text
MCP Client (e.g. Termux)
        |
        | HTTPS + OAuth 2.0 + PKCE
        v
Kali Linux MCP Server
        |
        +-- Streamable HTTP
        +-- Host validation
        +-- Rate limiting
        +-- OAuth authorization
        +-- Audit logging
        |
        v
Allowlisted read-only MCP tools
```

The client connects over the local network to:

```text
https://<MCP_PUBLIC_HOST>:<MCP_PORT>/mcp
```

## Available Tools

| Tool | Purpose |
| --- | --- |
| `kali_info` | Returns Kali/server information |
| `system_status` | Reports general system status |
| `disk_status` | Reports disk/storage information |
| `memory_status` | Reports memory information |
| `network_status` | Reports network status |
| `network_interfaces` | Lists network interface information |
| `read_text_file` | Reads permitted text-file content |

### `read_text_file` restrictions

`read_text_file` is deliberately restricted:

- Files must remain within the project workspace.
- Absolute paths are rejected.
- Path traversal is rejected.
- Symlink escapes outside the permitted workspace are rejected.
- Maximum readable file size is **1 MiB**.

New capabilities should be added as dedicated tools. Do not add generic command execution.

## Security Model

### Authentication and authorization

- OAuth 2.0 Authorization Code flow
- Refresh Token flow
- Public-client registration
- PKCE with S256
- Single supported MCP scope: `mcp:read`
- Resource validation
- Short-lived authorization requests and authorization codes
- Authorization codes are single-use
- Refresh tokens are stored hashed
- Token revocation is enabled
- Dynamic registration is limited to the supported scope

### PKCE

PKCE protects the authorization-code exchange for the public-client model used by this project.

The integration test verifies the S256 flow, including rejection of an incorrect code verifier.

### Token lifetimes

| Item | Default |
| --- | ---: |
| Authorization request | 300 s |
| Authorization code | 300 s |
| Access token | 900 s (15 min) |
| Refresh token | 2,592,000 s (30 days) |

### Transport security

- HTTPS only
- Minimum TLS 1.2
- Restricted ECDSA cipher suites
- DNS rebinding protection
- Explicit host allowlisting
- ECDSA P-256 certificates
- Certificate SAN validation
- Certificate/private-key matching checks

### Rate limiting

Rate limiting is applied to:

```text
/register
/authorize
/token
/revoke
/mcp
```

Default:

```text
10 requests / 60 seconds
```

Both values are configurable.

### Audit logging

Audit records are written to:

```text
logs/audit.log
```

Records include:

- Timestamp
- Tool name
- Sanitized arguments
- Execution status
- Result or error information

Sensitive keys are recursively redacted, including:

```text
api_key
authorization
client_secret
password
refresh_token
secret
token
```

The sanitizer handles nested dictionaries and sequences without modifying the original input.

## Threat Model and Limitations

This project reduces the blast radius of giving an AI client access to a Kali host. It does **not** make the host safe to expose to the public internet.

### Designed to protect against

- Arbitrary command execution through the MCP interface
- Unauthenticated access to protected tools
- Authorization-code interception risks addressed by PKCE
- DNS rebinding against the local server
- Brute-force and flooding of protected endpoints through rate limiting
- Sensitive values leaking into audit logs

### Not covered / known limitations

- Intended for use on a trusted local network
- Public internet exposure is not a supported deployment scenario
- The project has not been independently audited
- Dynamic client registration is available to clients that can reach the server; authorization still requires the configured consent flow
- The default certificate is self-signed
- Anything an authorized read-oriented tool can return can be viewed by the authorized client
- The rate limiter is process-local and does not provide distributed/shared rate-limit state

Review every tool before adding it to the allowlist.

## Configuration Reference

Configuration is controlled through environment variables defined in `config.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `MCP_PORT` | `8000` | Listening port |
| `MCP_PUBLIC_HOST` | `192.168.1.7` | Address clients use; change for your network |
| `MCP_ISSUER` | `https://<MCP_PUBLIC_HOST>:<MCP_PORT>` | OAuth issuer URL |
| `MCP_RESOURCE` | `<MCP_ISSUER>/mcp` | Protected resource URL |
| `JWT_ALGORITHM` | `EdDSA` | JWT signing algorithm |
| `MCP_PUBLIC_KEY_PATH` | `secrets/jwt-ed25519-public.pem` | JWT public key |
| `MCP_PRIVATE_KEY_PATH` | `secrets/jwt-ed25519-private.pem` | JWT private key |
| `OAUTH_DB_PATH` | `data/oauth.db` | SQLite OAuth database |
| `MCP_TLS_CERT_PATH` | `secrets/tls/mcp-server.crt` | TLS certificate |
| `MCP_TLS_KEY_PATH` | `secrets/tls/mcp-server.key` | TLS private key |
| `AUTHORIZATION_REQUEST_TTL_SECONDS` | `300` | Authorization request lifetime |
| `AUTHORIZATION_CODE_TTL_SECONDS` | `300` | Authorization code lifetime |
| `ACCESS_TOKEN_TTL_SECONDS` | `900` | Access token lifetime |
| `REFRESH_TOKEN_TTL_SECONDS` | `2592000` | Refresh token lifetime |
| `OAUTH_RATE_LIMIT` | `10` | Requests allowed per window |
| `OAUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window |

Keep private keys, OAuth state, and audit logs out of version control.

## Quick Start

### Prerequisites

- Kali Linux or another Linux host with Python 3 and `openssl`
- A **non-root** user
- A client that supports MCP over Streamable HTTP with OAuth

### 1. Install

```bash
git clone https://github.com/Zer-security/secure-mcp-server.git
cd secure-mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p logs data secrets/tls
```

### 2. Generate JWT signing keys

```bash
openssl genpkey -algorithm ED25519 -out secrets/jwt-ed25519-private.pem
openssl pkey -in secrets/jwt-ed25519-private.pem -pubout -out secrets/jwt-ed25519-public.pem
chmod 600 secrets/jwt-ed25519-private.pem
```

### 3. Generate the TLS certificate

```bash
PYTHONPATH=. python scripts/generate_tls.py
```

The generated certificate uses ECDSA P-256. Certificate handling includes certificate/key compatibility checks, SAN validation, backup, and rollback on promotion failure.

The default certificate is self-signed, so an MCP client must be configured to trust it.

### 4. Configure

Set the server's LAN address:

```bash
export MCP_PUBLIC_HOST=192.168.x.x
export MCP_PORT=8000
```

The server uses explicit host validation based on the configured public host and port.

### 5. Run

```bash
PYTHONPATH=. python server.py
```

The MCP endpoint is:

```text
https://<MCP_PUBLIC_HOST>:8000/mcp
```

The server refuses to run as root.

### 6. Connect a client

Point an MCP-compatible client at the MCP endpoint.

The authorization flow uses dynamic public-client registration, an interactive consent step, OAuth 2.0 Authorization Code flow, and PKCE S256.

## Testing

The release `v1.0.0` was verified with:

```text
124 passed
```

Historical full-suite command used for `v1.0.0`:

```bash
PYTHONPATH=. ./venv/bin/pytest -q
```

Current CI command:

```bash
PYTHONPATH=. pytest -q --ignore=tests/test_integration.py
```

Current CI verification: `123 passed`.

The suite covers:

- OAuth provider and integration flow
- Authentication
- Transport security
- TLS
- Rate limiting
- SSRF/network security
- Input validation
- File tools
- MCP tools
- Audit logging and sanitization
- Configuration

The release commit is:

```text
f642badaa27315e6b446e1b4370cf113fdc652e1
```

## Project Structure

```text
secure-mcp-server/
├── core/
│   ├── audit_extension.py
│   ├── audit_sanitizer.py
│   ├── oauth_provider.py
│   ├── oauth_routes.py
│   ├── rate_limit.py
│   ├── security.py
│   ├── ssrf.py
│   └── validation.py
├── scripts/
│   └── generate_tls.py
├── tools/
│   ├── file_tools.py
│   ├── info_tools.py
│   ├── network_tools.py
│   └── system_tools.py
├── tests/
├── config.py
├── server.py
├── test_client.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Development Principles

- Least privilege and explicit allowlisting
- Secure defaults
- No generic shell or command execution
- No hardcoded secrets
- Input validation
- Authentication before protected operations
- Auditability
- Fail-safe behavior
- Reproducible testing
- Evidence-based security claims

Workflow:

```text
Implement
   ↓
Test
   ↓
Verify
   ↓
Document
```

A feature should not be described as secure merely because it exists in source code. The implementation and relevant tests should be verified first.

## Roadmap

- [x] GitHub Actions CI with automated tests
- [ ] Dependency/update automation
- [ ] Additional read-only tools reviewed against the least-privilege model
- [ ] Documented MCP client setup guides
- [ ] Additional security hardening based on verified requirements

## Responsible Use

Use this software only on systems you own or are explicitly authorized to administer or test.

The project is intended for controlled, authorized environments and should not be treated as a general-purpose remote administration interface.

## Security Policy

If you discover a security vulnerability, avoid publishing sensitive details in a public issue.

Use the repository's GitHub Security Advisory mechanism for private vulnerability reporting.

## License

Licensed under the [Apache License 2.0](LICENSE).
