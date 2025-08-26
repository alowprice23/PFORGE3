-- Defines the schema for the nonce store, used to prevent replay attacks
-- on capability tokens.

-- When a capability token is verified, its unique nonce is added to this
-- table. Before verifying a new token, the system checks if its nonce
-- already exists here. If it does, the token is rejected.
CREATE TABLE IF NOT EXISTS capability_nonces (
  -- The nonce from the capability token, a unique UUID.
  nonce TEXT PRIMARY KEY NOT NULL,

  -- The operation ID associated with the token for audit purposes.
  op_id TEXT NOT NULL,

  -- The Unix timestamp when the nonce can be safely purged from the database.
  -- This should be set to the token's expiration time.
  expires_at INTEGER NOT NULL
);

-- An index to allow for efficient cleanup of expired nonces.
CREATE INDEX IF NOT EXISTS idx_nonces_expires_at ON capability_nonces (expires_at);
