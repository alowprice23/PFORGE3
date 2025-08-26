-- Defines the schema for the agentic CLI's "constellation" memory.
-- This database tracks the outcomes of CLI actions to enable learning.

-- The 'transitions' table records every single action taken by the agentic CLI.
-- It serves as the ground-truth log for backtesting and reward calculation.
CREATE TABLE IF NOT EXISTS transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,                      -- Timestamp of the transition
  context TEXT NOT NULL,                 -- A feature vector representing the state before the action
  action TEXT NOT NULL,                  -- The name of the skill/action taken (e.g., 'run_tests')
  command TEXT NOT NULL,                 -- The exact command executed
  rc INTEGER NOT NULL,                   -- The return code of the command
  stdout TEXT,                           -- A truncated log of the command's output
  before_metrics TEXT NOT NULL,          -- JSON blob of key metrics before the action
  after_metrics TEXT NOT NULL,           -- JSON blob of key metrics after the action
  reward REAL NOT NULL                   -- The calculated reward for this transition
);

-- The 'action_stats' table stores the learned value for each action in each context.
-- This is the core of the UCB1/Thompson sampling policy, allowing the CLI to
-- choose the best action based on past performance.
CREATE TABLE IF NOT EXISTS action_stats (
  context TEXT NOT NULL,
  action TEXT NOT NULL,
  n_pulls INTEGER NOT NULL,              -- The number of times this action has been tried in this context
  mean_reward REAL NOT NULL,             -- The running average reward for this action in this context
  PRIMARY KEY (context, action)
);

-- Indexes to speed up queries for policy decisions and route analysis.
CREATE INDEX IF NOT EXISTS idx_transitions_context_action ON transitions (context, action);
CREATE INDEX IF NOT EXISTS idx_transitions_reward ON transitions (reward);
