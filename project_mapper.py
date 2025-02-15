#!/usr/bin/env python3
"""
Simplified Project Mapper:
  - Build a directory tree mapping (grouped by file type)
  - Build a module-level dependency graph from Python import statements
  - Compare external libraries used vs. those declared in requirements.txt
  - Output a JSON report and a simplified Mermaid diagram of internal module dependencies

Usage:
  python simplified_project_mapper.py <project_root> [--output project_map.json] [--mermaid project_map.mmd] [--ignore-dir DIR1,DIR2,...]

Example:
  python simplified_project_mapper.py /path/to/your/project --output my_project_map.json --mermaid my_project_map.mmd --ignore-dir tools,tests
  
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

# Global list for additional directories to ignore (populated from command-line)
ADDITIONAL_IGNORE_DIRS = set()

def should_ignore(name):
    """Check if a file or directory name matches any ignore pattern."""
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def should_ignore_path(path):
    """Check if any component of the path should be ignored or is in the additional ignore list."""
    parts = path.split(os.sep)
    for part in parts:
        if should_ignore(part) or part in ADDITIONAL_IGNORE_DIRS:
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
        full_path = os.path.join(root, entry)
        if should_ignore_path(full_path):
            continue
        if os.path.isdir(full_path):
            tree["children"].append(build_directory_tree(full_path))
        else:
            if should_ignore(entry):
                continue
            file_type = classify_file(entry)
            tree["children"].append({
                "name": entry,
                "path": full_path,
                "type": file_type
            })
    return tree

def extract_imports_from_file(file_path):
    """
    Extract import statements from a Python file.
    For 'import' statements, return the module name.
    For 'from ... import ...' statements, return the full module name.
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
                # e.g., "import evaluation.models" -> "evaluation.models"
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # For relative imports (level > 0), we ignore the dots and use module if available.
            if node.module:
                imports.append(node.module)
    return list(set(imports))

def extract_config_loads(file_path):
    """
    Extract string literals from a file that look like config filenames.
    Looks for open() calls with a literal ending with .json, .yaml, or .yml.
    """
    config_files = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        return config_files

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Look for calls like open("some_config.yaml", ...)
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    val = arg.value
                    if val.endswith((".json", ".yaml", ".yml")):
                        config_files.append(val)
    return list(set(config_files))

def build_dependency_graph(root, directory_tree):
    """
    Walk through the directory and build a mapping of each Python file to its imports and config file loads.
    Differentiates internal (files within the project) and external imports.
    """
    dependency_graph = {}  # {file_path: {"internal": [], "external": [], "configs": []}}
    internal_modules = {}  # module_name -> file_path
    # First pass: collect internal module names using dotted notation from relative paths.
    for subdir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(subdir, d))]
        for file in files:
            if file.endswith(".py") and not should_ignore(file):
                file_path = os.path.join(subdir, file)
                rel_path = os.path.relpath(file_path, root)
                module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                internal_modules[module_name] = file_path
    # Second pass: build dependency graph for Python files.
    for subdir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(subdir, d))]
        for file in files:
            if file.endswith(".py") and not should_ignore(file):
                file_path = os.path.join(subdir, file)
                if should_ignore_path(file_path):
                    continue
                imports = extract_imports_from_file(file_path)
                config_loads = extract_config_loads(file_path)
                dependency_graph[file_path] = {"internal": [], "external": [], "configs": config_loads}
                for imp in imports:
                    # Try to match against any internal module (exact or as prefix)
                    matched = False
                    for mod_name, mod_path in internal_modules.items():
                        # If the import exactly matches or is a prefix of a module name, count as internal.
                        if mod_name == imp or mod_name.startswith(imp + "."):
                            dependency_graph[file_path]["internal"].append(mod_name)
                            matched = True
                    if not matched:
                        dependency_graph[file_path]["external"].append(imp)
                dependency_graph[file_path]["internal"] = list(set(dependency_graph[file_path]["internal"]))
                dependency_graph[file_path]["external"] = list(set(dependency_graph[file_path]["external"]))
    return dependency_graph, internal_modules

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

def flatten_directory_tree(tree):
    """
    Flatten the directory tree to a list of file nodes.
    Each node is a dict with keys: path, type.
    """
    files = []
    if tree["type"] != "directory":
        files.append(tree)
    else:
        for child in tree.get("children", []):
            files.extend(flatten_directory_tree(child))
    return files

def generate_mermaid_diagram(dependency_graph, internal_modules, root, directory_tree):
    """
    Generate a simplified Mermaid diagram for internal dependencies.
    Each node is a Python file (module) or a config file.
    Edges are drawn from a Python file to an internal module it imports,
    and from a Python file to a config file it loads.
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

    # Create nodes for Python files (using relative paths) based on dependency_graph keys.
    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        get_node_id(rel_path)  # reserve an ID

    # Also create nodes for config files found in the directory tree.
    all_files = flatten_directory_tree(directory_tree)
    config_files = {}
    for f in all_files:
        if f["type"] == "config":
            config_rel = os.path.relpath(f["path"], root)
            config_files[config_rel] = f["path"]
            get_node_id(config_rel)

    # Emit nodes for Python files.
    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        nid = get_node_id(rel_path)
        lines.append(f'{nid}["{rel_path}"]')
    # Emit nodes for config files.
    for config_rel in config_files.keys():
        nid = get_node_id(config_rel)
        lines.append(f'{nid}["{config_rel}"]')

    # Create edges for internal module imports.
    for file_path, deps in dependency_graph.items():
        src_rel = os.path.relpath(file_path, root)
        src_id = get_node_id(src_rel)
        for mod_name in deps["internal"]:
            # Look up the file path from internal_modules
            if mod_name in internal_modules:
                target_path = internal_modules[mod_name]
            else:
                # Try to find one where module name matches ending.
                target_path = None
                for m, fp in internal_modules.items():
                    if m.endswith(mod_name):
                        target_path = fp
                        break
            if target_path:
                tgt_rel = os.path.relpath(target_path, root)
                tgt_id = get_node_id(tgt_rel)
                lines.append(f'{src_id} --> {tgt_id}')
        # Create edges for config file loads.
        for conf in deps["configs"]:
            # If conf is a relative path, try to resolve relative to file_path directory.
            conf_path = os.path.join(os.path.dirname(file_path), conf)
            if not os.path.exists(conf_path):
                # Otherwise, assume conf is relative to project root.
                conf_path = os.path.join(root, conf)
            conf_rel = os.path.relpath(conf_path, root)
            # Only add if the config file exists in our directory tree.
            if conf_rel in config_files:
                tgt_id = get_node_id(conf_rel)
                lines.append(f'{src_id} --> {tgt_id}')
    return "\n".join(lines)

def main(root, output_json, mermaid_file):
    directory_tree = build_directory_tree(root)
    dependency_graph, internal_modules = build_dependency_graph(root, directory_tree)
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

    mermaid_code = generate_mermaid_diagram(dependency_graph, internal_modules, root, directory_tree)
    with open(mermaid_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    print(f"Mermaid diagram written to {mermaid_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simplified Project Mapper with Internal Import Matching, Config Loads, and Ignored Directories."
    )
    parser.add_argument("root", help="Root directory of the project")
    parser.add_argument("--output", "-o", default="project_map.json", help="Output JSON file (default: project_map.json)")
    parser.add_argument("--mermaid", default="project_map.mmd", help="Output Mermaid diagram file (default: project_map.mmd)")
    parser.add_argument("--ignore-dir", help="Comma-separated list of directory names to ignore (e.g. tools,tests)")
    args = parser.parse_args()

    if args.ignore_dir:
        for d in args.ignore_dir.split(","):
            ADDITIONAL_IGNORE_DIRS.add(d.strip())

    main(args.root, args.output, args.mermaid)
