# Project Mapper

## Why use this?
1. Working with AI to develop code (or just good documentation of a system architecture for that matter) you need a good understanding of how your system works.
2. You may want to make structural/architectural changes, etc and want to see what impact (direct/cascading) you'll have. What other areas require changes? etc.
3. This will easily document your project with you (human) and AI (machine) in mind

### Human vs Machine Communication
1. Machines and Humans process information differently: machines can handle lots of structured data in JSON, humans cannot
2. Specificity is key: communicate with the best method/medium for the entity needing the information. 

### This is a start, but not the finish
- This should give you a good starting point for both human‑ and machine‑readable mapping of your project’s functions, classes, and their interdependencies.
- Feel free to tweak the level of detail or the output formats as your needs evolve!

## Overview
This Python script walks a project’s directory tree, parses each Python file with Python’s built‑in AST module, and builds a JSON representation that maps out the modules, functions, and classes (with their methods). It also does a best‑effort scan inside each function/method to capture which functions they call (by looking at AST Call nodes). Finally, it can also output a simple Mermaid diagram (in Markdown format) to help you visualize the relationships if you wish. (You can later copy/paste the Mermaid code into Obsidian, VS Code preview, or any other Mermaid‑compatible viewer.)

You can adjust the level of granularity as needed. (For example, if you decide that nested helper functions are not interesting, you could modify the script to ignore them.) This script uses only standard libraries so it should run on Python 3.11/3.12 without extra dependencies.

## How It Works

1. **Parsing the Files:**  
   The script walks your project directory (ignoring directories like `.git` and `__pycache__`), and for every `.py` file, it uses the `ast` module to extract:
   - **Top-level functions:** Name, line number, argument list, docstring, and any function calls inside.
   - **Classes:** Name, line number, docstring, and for each method inside the class, similar details as functions.

2. **Capturing Function Calls:**  
   Inside each function (or method), the `FunctionCallVisitor` walks through the AST to collect calls. It handles both simple names (e.g. `foo()`) and attribute calls (e.g. `self.bar()` or `module.func()`).

3. **Generating Mermaid Diagrams:**  
   - **Full Mode:** In addition to modules, functions, classes, and methods, it includes nodes and edges for each function/method call.
   - **Summary Mode:** Omits the detailed function calls, showing only the primary structure.  
   You choose the mode via `--mermaid-mode`.

4. **Output Formats:**  
   - **JSON:** Contains a structured mapping of modules, functions, classes, and their relationships. This is ideal for machine‑to‑machine processing.
   - **Mermaid (optional):** Produces a simple diagram in Mermaid “graph TD” syntax that you can paste into tools like Obsidian or a Mermaid live editor for quick visual reference.

## Usage

Below is an updated version of the script that now supports two Mermaid output modes:

- **Full Mode:** Shows all details—including function/method calls.
- **Summary Mode:** Shows only high-level relationships (modules, functions, classes, and methods).

You can choose the mode via the command-line argument `--mermaid-mode` (default is `"full"`). This flexibility helps keep diagrams manageable if you have many edges.


4. **Usage Examples:**

   ```bash
   # Generate JSON mapping only
   python project_mapper.py /path/to/your/project -o my_project_map.json

   # Generate both JSON and a detailed Mermaid diagram
   python project_mapper.py /path/to/your/project -o my_project_map.json --mermaid my_project_map.mmd --mermaid-mode full

   # Generate both JSON and a summary Mermaid diagram
   python project_mapper.py /path/to/your/project -o my_project_map.json --mermaid my_project_map.mmd --mermaid-mode summary
   ```
