#!/usr/bin/env bash
# ruff + black + eslint

ruff pforge/
black --check pforge/
# eslint pforge/ui/src --max-warnings 0
