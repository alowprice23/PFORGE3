# PLAN: `tools/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `tools/` directory provides a library of safe, reliable, and idempotent code transformation utilities. These are the low-level, primitive "tools" that the `FixerAgent` uses to perform its work. By isolating these transformations into a dedicated, well-tested directory, we ensure that all code modifications are syntactically correct, predictable, and decoupled from the higher-level decision-making logic of the agents. This directory answers the question: "How can we safely and correctly perform a specific, common refactoring task?"

**Scope of Ownership**:

*   **AST/CST Utilities (`ast_utils.py`)**: It owns the foundational helpers for parsing source code into an Abstract Syntax Tree (AST) or Concrete Syntax Tree (CST), traversing the tree, and rendering a modified tree back into valid source code while preserving formatting.
*   **Import Management (`imports.py`)**: It owns the specific logic for adding, removing, and reordering import statements in a source file.
*   **Typing Assistance (`typing.py`)**: It owns the tools for programmatically adding or modifying type hints for variables and functions.
*   **Test Stabilization (`tests_stabilize.py`)**: It owns the utilities for wrapping test code in fixtures or context managers that make them deterministic (e.g., by freezing time or seeding randomness).
*   **External Formatter Hooks (`formatters.py`)**: It owns the safe wrappers for invoking external, command-line based tools like `black` and `ruff`.

**Explicitly Not in Scope**:

*   **Decision Making**: This directory is purely mechanical. It does not decide *when*, *why*, or *if* a transformation should be applied. That strategic logic resides entirely within the `agents/` (primarily the `FixerAgent` and `PlannerAgent`).
*   **The Agents Themselves**: It does not contain any agent implementations. It is a library that agents consume.
*   **The AST/CST Library**: It uses a library like `LibCST` but does not own it.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `tools/` directory as a Python package and to re-export the primary transformation functions for easy use by the `FixerAgent`.
*   **Interfaces**: Provides the public API for the code transformation toolkit.

### 2.2. `ast_utils.py`

*   **Responsibilities**: To provide the core, reusable utilities for tree-based code manipulation.
    *   `parse_to_cst(source_code: str) -> libcst.Module`: A robust function that parses a string of source code into a Concrete Syntax Tree, handling potential syntax errors gracefully.
    *   `render_from_cst(tree: libcst.Module) -> str`: A function that takes a modified CST and renders it back into a string of source code, preserving as much of the original formatting as possible.
    *   `find_nodes(tree: libcst.Module, node_type: Type[libcst.CSTNode]) -> list[libcst.CSTNode]`: A generic helper to find all nodes of a specific type within a tree.
*   **Dependencies**: `LibCST` library.
*   **Tests**: A `test_ast_utils.py` will test the parse-and-render round trip to ensure that it doesn't mangle code.

### 2.3. `imports.py`

*   **Responsibilities**: To provide all tools related to managing `import` statements.
    *   `add_import(tree: libcst.Module, module_name: str, object_name: Optional[str] = None) -> libcst.Module`: A function that intelligently adds a new `import` or `from ... import` statement to the top of a file, placing it correctly relative to other imports.
    *   `remove_unused_imports(tree: libcst.Module) -> libcst.Module`: A powerful tool that performs a static analysis of the tree to find all imported names that are not referenced, and then removes their corresponding import statements.
    *   `reorder_imports(source_code: str) -> str`: A wrapper around the `isort` library to programmatically sort imports.
*   **Tests**: A `test_imports.py` will have extensive tests for adding imports to empty files, files with existing imports, and for correctly identifying and removing unused imports in a variety of scenarios.

### 2.4. `typing.py`

*   **Responsibilities**: To provide tools for adding and modifying type hints.
    *   `add_function_return_hint(tree: libcst.Module, function_name: str, hint: str) -> libcst.Module`: Finds a function definition by name and adds or replaces its return type annotation.
    *   `add_param_hint(tree: libcst.Module, function_name: str, param_name: str, hint: str) -> libcst.Module`: Finds a specific parameter within a function and adds a type annotation.
*   **Tests**: A `test_typing.py` will use sample function definitions to verify that hints can be added correctly to functions with and without existing annotations.

### 2.5. `tests_stabilize.py`

*   **Responsibilities**: To provide tools for making non-deterministic tests stable and reproducible.
    *   `inject_pytest_fixture(tree: libcst.Module, test_name: str, fixture_name: str) -> libcst.Module`: Finds a test function by name and adds a new parameter to its definition, effectively applying a pytest fixture. This is used to inject fixtures like `freezer` (from `libfaketime`).
    *   `seed_randomness(tree: libcst.Module, test_name: str, seed: int = 42) -> libcst.Module`: Injects `random.seed(42)` at the beginning of a specified test function.
*   **Tests**: A `test_tests_stabilize.py` will test the injection of fixtures and seed calls into sample test functions.

### 2.6. `formatters.py`

*   **Responsibilities**: To provide safe, simple hooks for invoking external command-line formatters.
    *   `apply_black(source_code: str) -> str`: Takes a string of Python code, runs it through the `black` formatter via a `subprocess`, and returns the formatted string.
    *   `apply_ruff(source_code: str) -> str`: A similar wrapper for `ruff --fix`.
*   **Security**: This module must be hardened against command injection. It will use `subprocess.run` with an explicit list of arguments (e.g., `["black", "-"]`) and pass the source code via `stdin`, which is the safest method.
*   **Tests**: `test_formatters.py` will use mock `subprocess.run` calls to verify that the correct commands and arguments are being constructed.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **Syntactic Correctness and Idempotence**.

*   **Correctness**: By operating on the AST/CST, these tools guarantee that their output is always syntactically valid Python code. This avoids a whole class of bugs that can arise from naive string manipulation and is a prerequisite for the `FixerAgent`'s own correctness proofs.
*   **Idempotence**: The transformations are designed to be idempotent where possible. Running a formatter on already-formatted code produces no change. This property makes the tools safe to be used in automated, repetitive workflows.
*   **Effort (`Effort_j`)**: The application of a tool from this directory represents a quantum of "Effort" in the `P` formula. The `FixerAgent` uses these tools to expend that effort.

---

## 4. Routing & Awareness

This directory is a library of pure functions and has no awareness of the larger system. Its awareness is confined to the grammar and structure of the Python language. This intentional lack of awareness is a feature, as it keeps the tools simple, reusable, and easy to test.

---

## 5. Token & Budget Hygiene

These tools are deterministic, local, and do not consume any LLM tokens. They are the "cheap" alternative to calling an LLM. A key part of pForge's intelligence is the `FixerAgent`'s ability to recognize when a task (like sorting imports) can be accomplished with a cheap tool from this directory instead of an expensive LLM call.

---

## 6. Operational Flows

*   **A FixerAgent Uses a Tool**:
    1.  The `FixerAgent` receives a task, e.g., "Add `import os` to `file.py`".
    2.  It reads the content of `file.py` into a string.
    3.  It calls `ast_utils.parse_to_cst(content)` to get a syntax tree.
    4.  It calls `imports.add_import(tree, module_name="os")` to get a modified tree.
    5.  It calls `ast_utils.render_from_cst(modified_tree)` to get the new source code string.
    6.  It writes the new string back to the file in the sandbox.

---

## 7. Testing & Backtests

*   **Unit Tests**: This directory will have one of the highest unit test coverages in the project. Each transformation function will be tested with a wide array of input source code snippets to cover edge cases and ensure the output is always correct and well-formatted.
*   **Backtesting**: These tools are not directly backtested, but their correctness is a prerequisite for the backtesting of the `FixerAgent`. The `verifier` can confirm that a patch applied by the `FixerAgent` is syntactically valid, which is a direct result of the guarantees provided by this directory.

---

## 8. Security & Policy

*   **Safe Code Generation**: The primary security contribution of this directory is providing a safe, deterministic alternative to LLM-based code generation for common tasks. This reduces the attack surface associated with unpredictable LLM outputs.
*   **Hardened `formatters.py`**: The `formatters.py` module, which calls external processes, must be secure against command injection. It will achieve this by never using `shell=True` and by passing code via `stdin` rather than writing temporary files or including code in command-line arguments.

---

## 9. Readme Cross-Reference

The functions in this directory are the atomic "moves" that the puzzle solver in the `README.md` can perform. They are the fundamental operations that allow the system to manipulate the puzzle pieces.

| Tool Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `ast_utils.py` | The basic ability to pick up and put down a puzzle piece without breaking it. |
| `imports.py` | The ability to correctly connect the "tabs" and "slots" of two puzzle pieces (modules). |
| `typing.py` | The ability to look closely at the edge of a piece to understand its exact shape (its type) so you know what it can connect to. |
| `formatters.py` | The act of tidying and organizing a section of the puzzle, making it easier to see the overall picture and plan the next move. This directly reduces `H_style` (style entropy). |

This directory provides the essential, reliable "hands" that allow the `FixerAgent` to skillfully assemble the puzzle.
