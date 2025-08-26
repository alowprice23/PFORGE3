-- Defines the schema for the budget ledger, which provides a persistent,
-- auditable record of all LLM token expenditures.

-- This table creates a financial audit trail, allowing for detailed analysis
-- of token costs by vendor, agent, or time period.
CREATE TABLE IF NOT EXISTS token_spend (
  -- A unique ID for each recorded transaction.
  id INTEGER PRIMARY KEY AUTOINCREMENT,

  -- The Unix timestamp of the LLM API call.
  ts REAL NOT NULL,

  -- The vendor of the LLM (e.g., 'openai', 'anthropic', 'google').
  vendor TEXT NOT NULL,

  -- The operation ID that triggered the spend for causality tracking.
  op_id TEXT NOT NULL,

  -- The number of tokens in the prompt.
  prompt_tokens INTEGER NOT NULL,

  -- The number of tokens in the completion.
  completion_tokens INTEGER NOT NULL,

  -- The calculated cost of the API call in USD, based on the rates
  -- defined in `config/llm_providers.yaml`.
  cost_usd REAL NOT NULL
);

-- An index to allow for efficient querying by vendor or timestamp.
CREATE INDEX IF NOT EXISTS idx_token_spend_vendor_ts ON token_spend (vendor, ts);
