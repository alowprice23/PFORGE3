#!/usr/bin/env bash
# start uvicorn + optional UI; fakeredis fallback

python -m venv .venv && source .venv/bin/activate
pip install -r pforge/requirements.txt
# npm i --prefix pforge/ui
# uvicorn pforge.server.app:app --reload &
# npm run --prefix pforge/ui dev &
echo "pForge is running at http://localhost:8000"
echo "UI is running at http://localhost:5173"
