#!/usr/bin/env python3
"""
Simplified Project Mapper:
  - Build a directory tree mapping (grouped by file type)
  - Build a module-level dependency graph from Python import statements
  - Compare external libraries used vs. those declared in requirements.txt
  - Output a JSON report and a simplified Mermaid diagram of internal module dependencies

Usage:
  python project_mapper.py <project_root> [--output project_map.json] [--mermaid project_map.mmd]

Example:
  python project_mapper.py /path/to/your/project --output my_project_map.json --mermaid my_project_map.mmd

The JSON report will include:
  - directory_tree: A recursive view of your project directories and files with type classification (code, config, data, other)
  - dependency_graph: For each Python file, a list of internal and external modules imported
  - environment: Comparison of external libraries declared in requirements.txt versus those actually imported
      - declared_external_libs: Libraries declared in requirements.txt
      - used_external_libs: Libraries imported into your code
      - missing_declaration: Libraries used in code but missing from requirements.txt
      - unused_declaration: Libraries declared in requirements.txt but not used in code

The Mermaid diagram will provide a high-level visualization of internal module dependencies.
"""

import os
import ast
import json
import re
import argparse
import fnmatch

# Define file type categories based on extension
CODE_EXTENSIONS = {'.py'}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml'}
DATA_EXTENSIONS = {'.csv', '.tsv', '.xlsx', '.pdf', '.txt'}

# Define a list of ignore patterns for directories and files.
IGNORE_PATTERNS = [
    ".git", "__pycache__", ".ipynb_checkpoints", "venv", "env", "archive", "node_modules",
    "*.pyc", "*.pyo", ".DS_Store", "build", "dist", ".idea", ".pytest_cache", ".mypy_cache"
]

def should_ignore(name):
    """Check if a file or directory name matches any ignore pattern."""
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def classify_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in CODE_EXTENSIONS:
        return "code"
    elif ext in CONFIG_EXTENSIONS:
        return "config"
    elif ext in DATA_EXTENSIONS:
        return "data"
    else:
        return "other"

def build_directory_tree(root):
    """
    Recursively build a directory tree with files classified by type,
    ignoring directories or files that match the ignore patterns.
    """
    tree = {"name": os.path.basename(root), "path": root, "type": "directory", "children": []}
    try:
        entries = os.listdir(root)
    except PermissionError:
        return tree

    for entry in sorted(entries):
        if should_ignore(entry):
            continue
        full_path = os.path.join(root, entry)
        if os.path.isdir(full_path):
            tree["children"].append(build_directory_tree(full_path))
        else:
            file_type = classify_file(entry)
            if should_ignore(entry):
                continue
            tree["children"].append({
                "name": entry,
                "path": full_path,
                "type": file_type
            })
    return tree

def extract_imports_from_file(file_path):
    """
    Extract import statements from a Python file.
    Returns a list of imported module names.
    """
    imports = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split('.')[0])
    return list(set(imports))

def build_dependency_graph(root, directory_tree):
    """
    Walk through the directory and build a mapping of each Python file to its imports,
    ignoring files or directories that match the ignore patterns.
    Differentiates internal (files within the project) and external imports.
    """
    dependency_graph = {}  # {file_path: {"internal": [], "external": []}}
    internal_modules = set()
    # First pass: collect internal module names
    for subdir, dirs, files in os.walk(root):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for file in files:
            if file.endswith(".py") and not should_ignore(file):
                mod_name = os.path.splitext(file)[0]
                internal_modules.add(mod_name)
    # Second pass: build dependency graph
    for subdir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for file in files:
            if file.endswith(".py") and not should_ignore(file):
                file_path = os.path.join(subdir, file)
                imports = extract_imports_from_file(file_path)
                dependency_graph[file_path] = {"internal": [], "external": []}
                for imp in imports:
                    if imp in internal_modules:
                        dependency_graph[file_path]["internal"].append(imp)
                    else:
                        dependency_graph[file_path]["external"].append(imp)
                dependency_graph[file_path]["internal"] = list(set(dependency_graph[file_path]["internal"]))
                dependency_graph[file_path]["external"] = list(set(dependency_graph[file_path]["external"]))
    return dependency_graph

def read_requirements(root):
    """
    Read a requirements.txt file from the project root (if it exists).
    Returns a set of declared external libraries (lowercase).
    """
    req_path = os.path.join(root, "requirements.txt")
    declared = set()
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                pkg = re.split(r"[<=>]", line)[0].strip().lower()
                declared.add(pkg)
    return declared

def aggregate_external_usage(dependency_graph):
    """
    Aggregate external libraries imported across all python files.
    """
    used = set()
    for file_path, deps in dependency_graph.items():
        for ext in deps["external"]:
            used.add(ext.lower())
    return used

def generate_mermaid_diagram(dependency_graph, root):
    """
    Generate a simplified Mermaid diagram for internal dependencies.
    Each node is a Python file (module), and an edge exists if a file imports an internal module.
    """
    lines = ["graph TD"]
    node_ids = {}
    node_id_counter = 0

    def get_node_id(name):
        nonlocal node_id_counter
        if name not in node_ids:
            node_ids[name] = f"node{node_id_counter}"
            node_id_counter += 1
        return node_ids[name]

    for file_path, deps in dependency_graph.items():
        rel_path = os.path.relpath(file_path, root)
        src_id = get_node_id(rel_path)
        lines.append(f'{src_id}["{rel_path}"]')
        for internal in deps["internal"]:
            target = None
            for fp in dependency_graph.keys():
                if os.path.splitext(os.path.basename(fp))[0] == internal:
                    target = os.path.relpath(fp, root)
                    break
            if target:
                tgt_id = get_node_id(target)
                lines.append(f'{src_id} --> {tgt_id}')
    return "\n".join(lines)

def main(root, output_json, mermaid_file):
    directory_tree = build_directory_tree(root)
    dependency_graph = build_dependency_graph(root, directory_tree)
    declared_libs = read_requirements(root)
    used_libs = aggregate_external_usage(dependency_graph)
    missing_declaration = list(used_libs - declared_libs)
    unused_declaration = list(declared_libs - used_libs)
    
    report = {
        "directory_tree": directory_tree,
        "dependency_graph": dependency_graph,
        "environment": {
            "declared_external_libs": list(declared_libs),
            "used_external_libs": list(used_libs),
            "missing_declaration": missing_declaration,
            "unused_declaration": unused_declaration
        }
    }
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"JSON report written to {output_json}")

    mermaid_code = generate_mermaid_diagram(dependency_graph, root)
    with open(mermaid_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    print(f"Mermaid diagram written to {mermaid_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplified Project Mapper with Ignore Patterns: Directory tree, module dependencies, and environment comparison.")
    parser.add_argument("root", help="Root directory of the project")
    parser.add_argument("--output", "-o", default="project_map.json", help="Output JSON file (default: project_map.json)")
    parser.add_argument("--mermaid", default="project_map.mmd", help="Output Mermaid diagram file (default: project_map.mmd)")
    args = parser.parse_args()
    main(args.root, args.output, args.mermaid)
