-- Defines the schema for the PredictorAgent's risk model.
-- This database stores the parameters for the Bayesian learning model
-- that assesses the risk of editing different files.

CREATE TABLE IF NOT EXISTS risk_model (
  -- The path to the file, relative to the project root. This is the primary key.
  file_path TEXT PRIMARY KEY NOT NULL,

  -- The 'alpha' parameter of the Gamma/Beta distribution for this file,
  -- often representing the count of successful edits.
  alpha REAL NOT NULL,

  -- The 'beta' parameter of the Gamma/Beta distribution for this file,
  -- often representing the count of failed edits.
  beta REAL NOT NULL
);
