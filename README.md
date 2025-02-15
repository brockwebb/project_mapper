# Project Mapper

## Why use this?
1. Working with AI to develop code (or just good documentation of system architecture, for that matter), you need a good understanding of how your system works.
2. You may want to make structural/architectural changes and see what impact (direct/cascading) you'll have. What other areas require changes? etc.
3. This will easily document your project with you (human) and AI (machine) in mind

### Human vs Machine Communication
1. Machines and Humans process information differently: machines can handle lots of structured data in JSON, but humans cannot
2. Specificity is key: communicate with the best method/medium for the entity needing the information. 

## Overview
This should give you a clear, high-level overview and map of your project's structure, interdependencies, and environmental requirements in both human‑ and machine‑readable formats for optimal communication with each.

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
   It extracts the top-level module names from import statements for every Python file. It then distinguishes whether the module is internal (by matching against other Python files in the project) or external.

3. **Environment Comparison:**  
   It reads `requirements.txt` (if available) to list declared external libraries and then compares these with the libraries actually used in the code.

4. **Mermaid Diagram:**  
   A simplified Mermaid diagram is generated to show internal file dependencies (modules) by their relative paths.

5. **Outputs:**  
   - A JSON file that contains the directory tree, dependency graph, and environment delta.  
   - A Mermaid file you can load into any Mermaid viewer (or Obsidian) for a visual overview.

### How to Use:

1. **Save the Script:**  
   Save the script to a file named `project_mapper.py`.

2. **Run the Script:**  
   Open a terminal and navigate to the directory where the script is saved.

3. **Example Command Line Usage:**  
   To analyze a project located at `/path/to/your/project`, run:
   ```
   python project_mapper.py /path/to/your/project --output my_project_map.json --mermaid my_project_map.mmd
   ```
   - This will generate:
     - A JSON report named `my_project_map.json`
     - A Mermaid diagram file named `my_project_map.mmd`

4. **Review the Outputs:**  
   - Open the JSON report to inspect the directory tree, module dependency graph, and environment comparisons.
   - Load the Mermaid diagram in any Mermaid viewer (or Obsidian) to visualize the internal module dependencies.


