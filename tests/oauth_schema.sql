CREATE TABLE schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
CREATE TABLE oauth_clients (
        client_id TEXT PRIMARY KEY,
        client_secret TEXT,
        client_id_issued_at INTEGER NOT NULL,
        client_secret_expires_at INTEGER,
        client_name TEXT,
        redirect_uris_json TEXT NOT NULL,
        grant_types_json TEXT NOT NULL,
        response_types_json TEXT NOT NULL,
        scope TEXT,
        token_endpoint_auth_method TEXT NOT NULL,
        application_type TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_at INTEGER NOT NULL
    );
CREATE TABLE authorization_codes (
        code_hash TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        scopes TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        code_challenge TEXT NOT NULL,
        code_challenge_method TEXT NOT NULL,
        redirect_uri TEXT NOT NULL,
        redirect_uri_provided_explicitly INTEGER NOT NULL,
        resource TEXT,
        subject TEXT NOT NULL,
        consumed_at INTEGER,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (client_id)
            REFERENCES oauth_clients(client_id)
            ON DELETE CASCADE
    );
CREATE TABLE refresh_tokens (
        token_hash TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        scopes TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        resource TEXT,
        subject TEXT NOT NULL,
        issued_at INTEGER NOT NULL,
        revoked_at INTEGER,
        replaced_by_hash TEXT,
        FOREIGN KEY (client_id)
            REFERENCES oauth_clients(client_id)
            ON DELETE CASCADE
    );
CREATE INDEX idx_auth_codes_client_id
        ON authorization_codes(client_id);
CREATE INDEX idx_auth_codes_expires_at
        ON authorization_codes(expires_at);
CREATE INDEX idx_refresh_tokens_client_id
        ON refresh_tokens(client_id);
CREATE INDEX idx_refresh_tokens_expires_at
        ON refresh_tokens(expires_at);
CREATE TABLE authorization_requests (
        request_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        state TEXT,
        scopes TEXT NOT NULL,
        code_challenge TEXT NOT NULL,
        redirect_uri TEXT NOT NULL,
        redirect_uri_provided_explicitly INTEGER NOT NULL,
        resource TEXT,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        completed_at INTEGER,
        FOREIGN KEY (client_id)
            REFERENCES oauth_clients(client_id)
            ON DELETE CASCADE
    );
CREATE INDEX idx_auth_requests_client_id
        ON authorization_requests(client_id);
CREATE INDEX idx_auth_requests_expires_at
        ON authorization_requests(expires_at);
CREATE TABLE access_tokens (
        token_hash TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        scopes TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        resource TEXT,
        subject TEXT NOT NULL,
        jti TEXT NOT NULL UNIQUE,
        refresh_token_hash TEXT,
        issued_at INTEGER NOT NULL,
        revoked_at INTEGER,
        FOREIGN KEY (client_id)
            REFERENCES oauth_clients(client_id)
            ON DELETE CASCADE
    );
CREATE INDEX idx_access_tokens_client_id
        ON access_tokens(client_id);
CREATE INDEX idx_access_tokens_expires_at
        ON access_tokens(expires_at);
CREATE INDEX idx_access_tokens_refresh_hash
        ON access_tokens(refresh_token_hash);
