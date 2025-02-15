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
   - A D3 file you can load into any D3 viewer for an interactive visualization experience.

### How It Works:

1. **Command‑Line Options:**  
   - You supply the project folder path with `--path`.
   - Optionally, supply directories to ignore via `--ignore-dir`.

2. **Interactive Dialogue:**  
   - The script then asks for a base file name.
   - It creates three files in the project folder: `<base>_ai.json`, `<base>_mermaid.mmd`, and `<base>_d3.html`.

3. **Output Exclusion:**  
   - Files whose base names contain `_ai`, `_mermaid`, or `_d3` are ignored in the mapping.

4. **Mapping Generation:**  
   - The script builds the directory tree and dependency graph.
   - It outputs the JSON report, a Mermaid diagram, and a D3 HTML file for interactive viewing.

### Usage Example:

Run the script like this:

```
python project_mapper.py --path /path/to/your/project --ignore-dir tools,tests,data
```

Then, when prompted, enter a base file name (for example, "my_project_map"). The outputs will be created as:
- `/path/to/your/project/my_project_map_ai.json`
- `/path/to/your/project/my_project_map_mermaid.mmd`
- `/path/to/your/project/my_project_map_d3.html`

Open the D3 HTML file in your browser to interactively view your project mapping.

Let me know if you need further adjustments!

