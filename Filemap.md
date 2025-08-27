```text
pforge/
├─ README.md                                   – overview; quick start; local-only run; QED gates
├─ LICENSE
├─ CONTRIBUTING.md
├─ CODE_OF_CONDUCT.md
├─ CHANGELOG.md
├─ .gitignore
├─ .dockerignore
├─ .env.example                                – OPENAI_KEY, ANTHROPIC_KEY, GEMINI_KEY, REDIS_URL, LOCAL_ONLY=1
├─ requirements.txt                            – FastAPI, uvicorn, redis, pydantic, libCST, mypy, ruff, black, pytest, httpx, jinja2, prometheus-client, networkx, orjson, cryptography, sqlite-utils
├─ package.json                                – React/Vite front-end
├─ tsconfig.json
├─ Dockerfile                                  – optional (local-first emphasized)
├─ docker-compose.yml                          – optional (Redis/Prometheus/Grafana dev stack)
├─ Makefile                                    – convenience: preflight, doctor, test, lint, start
├─ pyproject.toml                              – tooling pins (ruff/black/mypy/pytest) (optional)
│
├─ config/
│  ├─ PLAN.md
│  ├─ settings.yaml                            – ports, feature flags, local-only, cadence, controller targets
│  ├─ llm_providers.yaml                       – model names/endpoints, cost per-token, max context, safety flags
│  ├─ agents.yaml                              – enabled agents, spawn weights, retry bounds, capability scopes
│  ├─ quotas.yaml                              – per-tenant CPU/RAM/token limits; burst and floor
│  ├─ seccomp.json                             – hardened shell profile (platform-gated)
│  ├─ allowlists.yaml                          – shell command/args allowlist; domain allowlist for egress
│  └─ policies.yaml                            – gating policy (blocking vs non-blocking φ, QED window, CVaR α)
│
├─ policies/
│  ├─ PLAN.md
│  ├─ signing/
│  │  ├─ public.pem                            – event verification key
│  │  └─ rotate.md                             – key rotation process
│  └─ redaction/
│     ├─ patterns.yaml                         – secret regexes; file/path denylist
│     └─ samples.md                            – examples & tests for redaction
│
├─ orchestrator/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ core.py                                  – tick loop; global snapshot Σ; op_id generation; CAS bindings
│  ├─ scheduler.py                             – adaptive economy; PI controller; concurrency updates
│  ├─ agent_registry.py                        – discovery/DI for agents; lifecycles
│  ├─ state_bus.py                             – in-mem snapshot store; pub/sub façade
│  ├─ efficiency_engine.py                     – 𝔈, entropy H components, EMA stability
│  ├─ signals.py                               – AMP dataclasses (ΔE, ΔM, φ results, QED, RECOVERY.*)
│  ├─ qedsupervisor.py                         – completion predicate & gates; co-signs proofs
│  └─ router.py                                – logical routing: file vs directory edit strategy via dep graph
│
├─ proof/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ bundle.py                                – build/validate proof bundles; attach tree_sha & venv_lock_sha
│  ├─ verifier.py                              – backtesting verifier (recompute hashes, test proofs, signatures)
│  ├─ signatures.py                            – ed25519/HMAC sign/verify; AMP envelope
│  ├─ capabilities.py                          – capability tokens (cap, scope, actor, exp, nonce)
│  ├─ redaction.py                             – scrub secrets from payload; counts & witnesses
│  └─ backtest_cli.py                          – `pforge verify` across a session; KPIs (Precision@Action, escapes)
│
├─ messaging/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ amp.py                                   – AMP schema, event codecs; idempotency keys
│  └─ redis_stream.py                          – Redis Streams wrapper; WS mirror hook
│
├─ storage/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ cas.py                                   – content-addressed snapshot store; trees, diffs, blobs
│  ├─ sqlite/
│  │  ├─ constellation_schema.sql              – context→route→reward tables
│  │  ├─ nonces_schema.sql                     – capability nonces (replay guard)
│  │  └─ budget_ledger_schema.sql              – per-vendor token spend
│  └─ fslock.py                                – file/dir locks for atomic write in sandbox/var
│
├─ planner/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ priority.py                              – Impact×Frequency / (Effort×Risk); CVaR formulation
│  ├─ solver_ilp.py                            – exact knapsack (if available); records approx gaps
│  ├─ solver_greedy.py                         – fallback solver with gap estimate and duals
│  ├─ budgets.py                               – time/token accounting; dual price estimation
│  └─ objectives.py                            – multi-objective blend (ΔE, stability, risk penalties)
│
├─ validation/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ selection.py                             – targeted test selection (RDep + coverage) with guards
│  ├─ types.py                                 – delta typecheck (mypy/pyright subset runner)
│  ├─ test_runner.py                           – pytest invoker; JUnit hash; full audit tracker
│  ├─ coverage_index.py                        – build/read coverage map; staleness detection
│  └─ dep_graph.py                             – import graph indexer (LibCST); reverse-closure utils
│
├─ recovery/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ preflight.py                             – prerequisite lattice μ; unsat core; fixpoint loop
│  ├─ detectors/
│  │  ├─ runtime_versions.py                   – Python/Node/Java checks vs lock ranges
│  │  ├─ packages.py                           – pip check, missing wheels, npm dry-run
│  │  ├─ services.py                           – Redis/DB probes; fakeredis fallback
│  │  ├─ ports.py                              – EADDRINUSE & PID witness
│  │  ├─ secrets.py                            – env var presence (never logs values)
│  │  ├─ time_tz.py                            – TZ/clock nondeterminism; flakiness CI
│  │  ├─ data_migrations.py                    – schema/migration DAG detection
│  │  └─ tooling_drift.py                      – mypy/pytest/ruff/black version skew
│  └─ actions/
│     ├─ env_relock.py                         – compute venv_lock_sha; unify tool locks
│     ├─ pkg_resolve.py                        – repair/install using local cache; pip check=0
│     ├─ service_boot.py                       – start fakeredis/embedded db; readiness probe
│     ├─ port_reassign.py                      – choose free port; config diff
│     ├─ clock_freeze.py                       – test fixtures for deterministic time
│     ├─ tz_set.py                             – enforce TZ=UTC for test run
│     └─ migrate_seed.py                       – sandbox DB migrations & seed with checksums
│
├─ agents/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ base_agent.py                            – lifecycle; AMP helpers; bounded retries
│  ├─ observer_agent.py                        – evidence graph; entropy H; metrics sampling
│  ├─ spec_oracle_agent.py                     – evaluate Φ; unsat cores; witnesses
│  ├─ predictor_agent.py                       – risk priors β (conservative logistic)
│  ├─ planner_agent.py                         – plan w/ budgets; ILP/greedy; CVaR α; duals & gaps
│  ├─ fixer_agent.py                           – AST-safe transforms; refinement bandit; targeted tests
│  ├─ misfit_agent.py                          – detect/flag edits that raise H or violate Φ (non-blocking)
│  ├─ false_piece_agent.py                     – dead deps/files; removal plans
│  ├─ backtracker_agent.py                     – minimal hitting set retractions
│  ├─ conflict_detector_agent.py               – build conflict graph Γ; compute hitting sets
│  ├─ efficiency_analyst_agent.py              – compute ΔE; EMA stability; flakiness CI
│  ├─ intent_router_agent.py                   – NL→intent→skill routes; safety grounding
│  ├─ recovery_agent.py                        – orchestrates preflight μ and RECOVERY.* proofs
│  ├─ self_repair_agent.py                     – periodic health checks; index refresh; cache warm
│  └─ summarizer_agent.py                      – user-facing diffs/explanations; terse, verifiable summaries
│
├─ tools/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ imports.py                               – localize/break cycles; reorder; remove unused
│  ├─ typing.py                                – add stubs; narrow casts; typing imports
│  ├─ tests_stabilize.py                       – clock/randomness fixtures; network fixture swap
│  ├─ formatters.py                            – black/ruff hooks; style normalization
│  └─ ast_utils.py                             – LibCST wrappers; idempotent edits; edit distance
│
├─ llm_clients/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ gemini_client.py                         – high-context reader; safety preface; local-only guard
│  ├─ claude_client.py                         – chain-of-thought coder (tool prompts); guardrails
│  ├─ openai_o3_client.py                      – precision bug-finder; suggestion scorer
│  ├─ retry.py                                 – exp backoff + jitter; transient handling
│  ├─ budget_meter.py                          – per-vendor token meter; soft/hard caps; ledger (SQLite)
│  └─ guardrails.py                            – refuse on secrets/egress/capability misuse
│
├─ sandbox/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ fs_manager.py                            – copy repo→sandbox; worktrees; snapshot/rollback
│  ├─ diff_utils.py                            – unified diff + color; summary for CLI
│  ├─ merge_back.py                            – three-way merge; conflict flags; CAS updates
│  └─ path_policy.py                           – enforce sandbox scope; traversal protection
│
├─ server/
│  ├─ PLAN.md
│  ├─ app.py                                   – FastAPI entrypoint; WS bridge (AMP/metrics)
│  ├─ middleware/
│  │  ├─ auth.py                               – JWT/API key
│  │  ├─ authz.py                              – capability enforcement; nonce replay guard
│  │  ├─ budget_guard.py                       – per-request token cap; vendor meter
│  │  ├─ throttle.py                           – shell cmd rate limits
│  │  └─ redaction.py                          – payload scrub on all emits
│  ├─ routes/
│  │  ├─ chat.py                               – POST /chat (agentic CLI), SSE /events
│  │  ├─ metrics.py                            – GET /metrics (Prometheus)
│  │  ├─ files.py                              – download sandbox files; diff endpoints
│  │  └─ proofs.py                             – GET /proofs/{id}; verify on demand
│  ├─ websocket/
│  │  └─ consumer.py                           – live agent log/event stream
│  └─ templates/
│     ├─ base.html
│     ├─ dashboard.html                        – efficiency, entropy, planner, controller
│     └─ chat.html                             – conversational CLI UI
│
├─ ui/
│  ├─ PLAN.md
│  ├─ public/
│  │  └─ favicon.ico
│  └─ src/
│     ├─ index.tsx
│     ├─ App.tsx
│     ├─ api/client.ts                         – fetch AMP/metrics/proofs
│     ├─ components/
│     │  ├─ ChatWindow.tsx
│     │  ├─ MetricsPanel.tsx
│     │  ├─ PlannerPanel.tsx
│     │  ├─ ProofViewer.tsx
│     │  ├─ DiffCard.tsx
│     │  ├─ ConstellationGraph.tsx
│     │  └─ AgentLog.tsx
│     └─ utils/llmColors.ts
│
├─ cli/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ main.py                                  – `pforge` entrypoint; conversational loop
│  ├─ chat.py                                  – NL intent parser; grounding; safety prompts
│  ├─ routes/
│  │  ├─ registry.yaml                         – skill graph nodes/edges with guard conditions
│  │  └─ learned.sqlite                         – constellation memory store (if running headless)
│  ├─ skills/
│  │  ├─ status.py                             – summarize Σ; gate health
│  │  ├─ doctor.py                             – run targeted fix cycle; audit before “done”
│  │  ├─ preflight.py                          – run μ; show unsat core & plan
│  │  ├─ fix.py                                – apply operator plan; bounded retries
│  │  ├─ verify.py                             – run backtests; print KPIs
│  │  ├─ routes.py                             – replay best route for context; explain reward
│  │  ├─ proofs.py                             – show latest proofs; diff summaries
│  │  └─ budget.py                             – token spend; caps; vendor splits
│  └─ prompts/
│     ├─ system_puzzle.md                      – math/constraints preface for LLM tools
│     ├─ fixer_guard.md                        – “no side-effect without capability”; diff-only output
│     ├─ router_guard.md                       – when to choose file vs directory edits
│     └─ summarizer_style.md                   – terse, verifiable diffs & rationale
│
├─ metrics/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ metrics_collector.py                     – push counters/gauges; register KPIs
│  └─ prometheus_exporter.py                   – serve /metrics; labels for agents & stages
│
├─ docs/
│  ├─ PLAN.md
│  ├─ architecture.md                          – end-to-end diagrams; agents; bus; CAS
│  ├─ runbook.md                               – on-call procedures; failure drills
│  ├─ api_reference.md                         – REST/WS; AMP schemas
│  ├─ prompt_library.md                        – canonical prompts; versioned; safety banners
│  ├─ math_proofs.md                           – Σ, Φ, 𝔈, H, β, P, CVaR; QED; hitting sets; proofs
│  ├─ safety_policy.md                         – capabilities, redaction, egress, locks
│  └─ backtesting_guide.md                     – how to verify all claims locally
│
├─ tests/
│  ├─ PLAN.md
│  ├─ __init__.py
│  ├─ unit/
│  │  ├─ test_efficiency_engine.py
│  │  ├─ test_entropy_metric.py
│  │  ├─ test_selection_reverse_closure.py
│  │  ├─ test_coverage_selection.py
│  │  ├─ test_delta_typecheck.py
│  │  ├─ test_refine_policy.py
│  │  └─ test_capabilities_and_redaction.py
│  ├─ integration/
│  │  ├─ onboarding_flow_test.py
│  │  ├─ solve_cycle_test.py
│  │  ├─ merge_conflict_test.py
│  │  ├─ targeted_then_full_test.py
│  │  ├─ recovery_preflight_test.py
│  │  └─ throttle_control_test.py
│  └─ e2e/
│     ├─ smoke_local_no_docker.py
│     └─ qed_gate_end_to_end.py
│
├─ scripts/
│  ├─ bootstrap.sh                             – venv; install; seed data; start local services if allowed
│  ├─ run_tests.sh                             – pytest + UI unit tests
│  ├─ preflight_check.sh                       – quick μ; prints unsat core
│  └─ fix_aioredis_direct.py                   – py3.12 compat shim (if needed)
│
├─ devops/
│  ├─ PLAN.md
│  ├─ k8s/                                     – optional cloud manifests
│  │  ├─ namespace.yaml
│  │  ├─ deployment.yaml
│  │  ├─ service.yaml
│  │  └─ hpa.yaml
│  ├─ grafana/
│  │  └─ dashboards/efficiency_dashboard.json
│  ├─ prometheus/prometheus.yml
│  └─ ci/
│     ├─ github_actions.yml
│     └─ docker_build.yml
│
├─ data/
│  ├─ PLAN.md
│  ├─ sample_repos/
│  │  └─ tiny_todo_app.zip
│  └─ puzzlebench/
│     ├─ metadata.json
│     └─ repos/                               – *.tar.gz sample repos for benchmarking
│
├─ var/
│  ├─ PLAN.md
│  ├─ index/
│  │  ├─ coverage.json                         – last coverage map (with SHA)
│  │  └─ dep_graph.json                        – import graph index (with SHA)
│  ├─ logs/
│  │  ├─ amp.jsonl                             – AMP rollup (redacted)
│  │  └─ metrics.jsonl
│  └─ db/
│     └─ constellation.sqlite                  – route memory; nonces; budget ledger
│
└─ verifiers/
   ├─ PLAN.md
   ├─ __init__.py
   ├─ precision_at_action.py                   – recompute Precision@Action from proofs
   ├─ escape_rate.py                           – targeted→full audit escapes
   ├─ conflict_minimality.py                   – check hitting set minimality
   ├─ qed_gate_audit.py                        – ensure all QED gates were satisfied
   └─ kpi_report.py                            – ΔE/min, rollbacks, focus score
```

**Why this file map is complete for your goals**

* **Agentic, natural-language CLI with self-awareness**
  `cli/` (chat parser, skills, route memory) + `agents/intent_router_agent.py` give a conversational interface that **knows** system state (`status.py`), routes to the right skills, and can replay the best learned route (`routes.py`). Constellation memory lives in SQLite.

* **Advanced puzzle system & math baked in**
  The formalism lives in `docs/math_proofs.md`, is implemented in `orchestrator/efficiency_engine.py`, `planner/priority.py` (CVaR), `validation/*` (targeted tests, delta typecheck), `agents/*` (unsat cores, hitting sets), and is **provable** via `proof/*` and `verifiers/*`.

* **Self-repairing**
  `agents/self_repair_agent.py` runs periodic health checks, index refreshes, and cache warms; `recovery/preflight.py` and `recovery/actions/*` enforce the prerequisite fixpoint before any semantic edits.

* **Token budgeting & cost control**
  `llm_clients/budget_meter.py` plus `server/middleware/budget_guard.py` enforce per-vendor caps; `planner/budgets.py` treats time/tokens as scarce resources with dual prices.

* **Clear diffs & user awareness in CLI**
  `sandbox/diff_utils.py` summarizes changes; `agents/summarizer_agent.py` produces concise, verifiable explanations; `cli/skills/proofs.py` and `ProofViewer.tsx` surface proofs and diffs on demand.

* **Logical routing: single file vs directory**
  `orchestrator/router.py` consults `validation/dep_graph.py` to expand edits file→closure when relationships warrant; `cli/prompts/router_guard.md` pins the policy for LLM tools.

* **Prerequisite logic (don’t fix code when the world is broken)**
  `recovery/detectors/*`, `recovery/actions/*`, and `recovery/preflight.py` turn missing packages/services/ports/timezone into **blocking constraints** with RECOVERY.\* proofs.

* **Backtestable, scientific**
  Every state change is an AMP event with a verifiable `proof/bundle.py`. Independent scripts in `verifiers/` recompute KPIs (Precision\@Action, escape rate, conflict minimality, QED gate audit) from *only* local artifacts.

* **End-state awareness**
  `orchestrator/qedsupervisor.py` encodes the **completion predicate** (all blocking φ true, full audit since last patch, empty Γ, safety/stability green). No “endless fixing.”

This structure is intentionally **local-first**: you can run everything without Docker, with fakeredis, and verify every claim offline. If you want, I can now generate a minimal *scaffold* (empty files with headers) so your team can start filling in modules in a safe order.
