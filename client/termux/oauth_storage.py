import json
from pathlib import Path

from mcp.client.auth import TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


STORAGE_PATH = Path(__file__).resolve().parent / ".oauth_tokens.json"


class FileTokenStorage(TokenStorage):
    def _read(self) -> dict:
        if not STORAGE_PATH.exists():
            return {}
        try:
            return json.loads(STORAGE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        STORAGE_PATH.write_text(json.dumps(data))
        STORAGE_PATH.chmod(0o600)

    async def get_tokens(self) -> OAuthToken | None:
        data = self._read()
        raw = data.get("tokens")
        if raw is None:
            return None
        return OAuthToken.model_validate(raw)

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._read()
        data["tokens"] = tokens.model_dump(mode="json")
        self._write(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        data = self._read()
        raw = data.get("client_info")
        if raw is None:
            return None
        return OAuthClientInformationFull.model_validate(raw)

    async def set_client_info(
        self, client_info: OAuthClientInformationFull
    ) -> None:
        data = self._read()
        data["client_info"] = client_info.model_dump(mode="json")
        self._write(data)
