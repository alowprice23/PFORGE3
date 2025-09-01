#!/usr/bin/env bash
# create demo_buggy/ sample & tests

mkdir -p pforge/demo_buggy
echo "def f(): return 1" > pforge/demo_buggy/bug1.py
echo "import os; print(os.environ['missing'])" > pforge/demo_buggy/bug2.py
echo "const a = 1;" > pforge/demo_buggy/bug3.tsx
echo "package main; func main() { }" > pforge/demo_buggy/bug4.go
