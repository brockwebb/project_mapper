# Project Mapper

## Why use this?
1. Working with AI to develop code (or just good documentation of system architecture, for that matter), you need a good understanding of how your system works.
2. You may want to make structural/architectural changes and see what impact (direct/cascading) you'll have. What other areas require changes? etc.
3. This will easily document your project with you (human) and AI (machine) in mind

### Human vs Machine Communication
1. Machines and Humans process information differently: machines can handle lots of structured data in JSON, but humans cannot
2. Specificity is key: communicate with the best method/medium for the entity needing the information. 

## Overview
This should give you a clear, high-level map of your project's structure and interdependencies in both human‑ and machine‑readable formats for optimal communication with each.

• Recursively builds a directory tree and classifies files (code, config, data).  
• For each Python file, it parses the imports to build a module-level dependency graph.  
• Reads a requirements.txt (if present) to list declared external libraries and compares them to what's actually imported.  
• Outputs a JSON structure with the directory tree, dependency graph, and environment block.  
• Also generates a simplified Mermaid diagram (only internal dependencies).

You can tweak file classifications or dependency heuristics as needed.

### How It Works:
1. **Directory Tree:**  
   The script recursively builds a tree of directories and files with a simple classification (code, config, data, other).

2. **Dependency Graph:**  
   For every Python file, it extracts the top-level module names from import statements. It then distinguishes whether the module is internal (by matching against other Python files in the project) or external.

3. **Environment Comparison:**  
   It reads `requirements.txt` (if available) to list declared external libraries and then compares these with the libraries actually used in the code.

4. **Mermaid Diagram:**  
   A simplified Mermaid diagram is generated to show internal file dependencies (modules) by their relative paths.

5. **Outputs:**  
   - A JSON file that contains the directory tree, dependency graph, and environment delta.  
   - A Mermaid file you can load into any Mermaid viewer (or Obsidian) for a visual overview.


