#!/usr/bin/env python3
"""
Simplified Project Mapper with Interactive Dialogue

This script will:
  a) Ask for the path to your project folder (outputs will be saved in that folder).
  b) Ask for a base file name for outputs. It will then create three output files:
       - <base>_ai.json   : the JSON report (mapping)
       - <base>_mermaid.mmd : the Mermaid diagram
       - <base>_d3.html   : the D3 interactive visualization HTML file
  c) Ask for a comma-separated list of directory names to ignore.
  d) Automatically ignore files whose base names contain "_ai", "_mermaid", or "_d3"
     (so that your output files are not re-processed).

Outputs will be saved in the project folder.
"""

import os
import ast
import json
import re
import fnmatch

# Define file type categories based on extension
CODE_EXTENSIONS = {'.py'}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml'}
DATA_EXTENSIONS = {'.csv', '.tsv', '.xlsx', '.pdf', '.txt'}

# Built-in ignore patterns for directories and files.
IGNORE_PATTERNS = [
    ".git", "__pycache__", ".ipynb_checkpoints", "venv", "env", "archive", "node_modules",
    "*.pyc", "*.pyo", ".DS_Store", "build", "dist", ".idea", ".pytest_cache", ".mypy_cache"
]

# Global set for additional directories to ignore (populated from interactive input)
ADDITIONAL_IGNORE_DIRS = set()

def should_ignore(name):
    """Return True if the file or directory name matches any built-in ignore pattern."""
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def should_ignore_output_file(filename):
    """Return True if the file's base name contains one of the output suffixes."""
    base = os.path.splitext(filename)[0]
    for substr in ["_ai", "_mermaid", "_d3"]:
        if substr in base:
            return True
    return False

def should_ignore_path(path):
    """
    Return True if any component of the path matches an ignore pattern or is in the additional ignore list.
    """
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
    ignoring directories or files that match ignore patterns or output files.
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
            if should_ignore(entry) or should_ignore_output_file(entry):
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
    For 'from ... import ...' statements, return the module.
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
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return list(set(imports))

def extract_config_loads(file_path):
    """
    Extract string literals that look like config filenames.
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
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    val = arg.value
                    if val.endswith((".json", ".yaml", ".yml")):
                        config_files.append(val)
    return list(set(config_files))

def build_dependency_graph(root, directory_tree):
    """
    Walk through the directory and build a mapping of each Python file to its imports and config loads.
    Differentiates internal (project files) and external imports.
    """
    dependency_graph = {}  # {file_path: {"internal": [], "external": [], "configs": []}}
    internal_modules = {}  # module_name -> file_path
    # First pass: Collect internal module names using dotted notation from relative paths.
    for subdir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(subdir, d))]
        for file in files:
            if file.endswith(".py") and not should_ignore(file) and not should_ignore_output_file(file):
                file_path = os.path.join(subdir, file)
                rel_path = os.path.relpath(file_path, root)
                module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                internal_modules[module_name] = file_path
    # Second pass: Build the dependency graph.
    for subdir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(subdir, d))]
        for file in files:
            if file.endswith(".py") and not should_ignore(file) and not should_ignore_output_file(file):
                file_path = os.path.join(subdir, file)
                if should_ignore_path(file_path):
                    continue
                imports = extract_imports_from_file(file_path)
                config_loads = extract_config_loads(file_path)
                dependency_graph[file_path] = {"internal": [], "external": [], "configs": config_loads}
                for imp in imports:
                    matched = False
                    # Match against internal modules using dotted notation.
                    for mod_name in internal_modules.keys():
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
    Read a requirements.txt file (if present) from the project root.
    Returns a set of declared external libraries (in lowercase).
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
    Aggregate external libraries imported across all Python files.
    """
    used = set()
    for file_path, deps in dependency_graph.items():
        for ext in deps["external"]:
            used.add(ext.lower())
    return used

def flatten_directory_tree(tree):
    """
    Flatten the directory tree into a list of file nodes.
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
    Generate a simplified Mermaid diagram.
    Each node is a Python file (module) or a config file.
    Draws edges from a file to an internal module it imports and from a file to a config file it loads.
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

    module_names = {}
    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
        module_names[file_path] = module_name

    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        get_node_id(rel_path)

    all_files = flatten_directory_tree(directory_tree)
    config_files = {}
    for f in all_files:
        if f["type"] == "config":
            rel = os.path.relpath(f["path"], root)
            config_files[rel] = f["path"]
            get_node_id(rel)

    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        nid = get_node_id(rel_path)
        lines.append(f'{nid}["{rel_path}"]')
    for conf_rel in config_files.keys():
        nid = get_node_id(conf_rel)
        lines.append(f'{nid}["{conf_rel}"]')

    for file_path, deps in dependency_graph.items():
        src_rel = os.path.relpath(file_path, root)
        src_id = get_node_id(src_rel)
        for mod_name in deps["internal"]:
            target_path = internal_modules.get(mod_name)
            if not target_path:
                for m, fp in internal_modules.items():
                    if m.endswith(mod_name):
                        target_path = fp
                        break
            if target_path:
                tgt_rel = os.path.relpath(target_path, root)
                tgt_id = get_node_id(tgt_rel)
                lines.append(f'{src_id} --> {tgt_id}')
        for conf in deps["configs"]:
            conf_path = os.path.join(os.path.dirname(file_path), conf)
            if not os.path.exists(conf_path):
                conf_path = os.path.join(root, conf)
            conf_rel = os.path.relpath(conf_path, root)
            if conf_rel in config_files:
                tgt_id = get_node_id(conf_rel)
                lines.append(f'{src_id} --> {tgt_id}')
    return "\n".join(lines)

def generate_d3_data(dependency_graph, internal_modules, root, directory_tree):
    """
    Convert the dependency graph into a D3-friendly JSON structure with "nodes" and "links".
    Nodes are created for each Python file (module) and for config files.
    """
    nodes = []
    links = []
    node_index = {}
    
    for file_path in dependency_graph.keys():
        rel_path = os.path.relpath(file_path, root)
        node = {"id": rel_path, "label": rel_path, "type": "code"}
        node_index[rel_path] = len(nodes)
        nodes.append(node)
    
    all_files = flatten_directory_tree(directory_tree)
    config_nodes = {}
    for f in all_files:
        if f["type"] == "config":
            rel = os.path.relpath(f["path"], root)
            config_nodes[rel] = f["path"]
            if rel not in node_index:
                node_index[rel] = len(nodes)
                nodes.append({"id": rel, "label": rel, "type": "config"})
    
    for src_path, deps in dependency_graph.items():
        src_rel = os.path.relpath(src_path, root)
        for mod_name in deps["internal"]:
            target_path = internal_modules.get(mod_name)
            if not target_path:
                for m, fp in internal_modules.items():
                    if m.endswith(mod_name):
                        target_path = fp
                        break
            if target_path:
                tgt_rel = os.path.relpath(target_path, root)
                if src_rel in node_index and tgt_rel in node_index:
                    links.append({"source": src_rel, "target": tgt_rel, "type": "import"})
        for conf in deps["configs"]:
            conf_path = os.path.join(os.path.dirname(src_path), conf)
            if not os.path.exists(conf_path):
                conf_path = os.path.join(root, conf)
            conf_rel = os.path.relpath(conf_path, root)
            if conf_rel in config_nodes and src_rel in node_index:
                links.append({"source": src_rel, "target": conf_rel, "type": "config"})
    
    return {"nodes": nodes, "links": links}

def generate_d3_html(d3_data, output_html):
    """
    Generate an HTML file that loads D3.js and displays a force-directed graph using d3_data.
    """
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Project Map D3 Visualization</title>
  <style>
    .link {{
      stroke: #999;
      stroke-opacity: 0.6;
    }}
    .node {{
      stroke: #fff;
      stroke-width: 1.5px;
    }}
    text {{
      font-family: sans-serif;
      font-size: 10px;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <svg width="960" height="600"></svg>
  <script src="https://d3js.org/d3.v5.min.js"></script>
  <script>
    var graph = {json.dumps(d3_data)};

    var svg = d3.select("svg"),
        width = +svg.attr("width"),
        height = +svg.attr("height");

    var color = d3.scaleOrdinal(d3.schemeCategory10);

    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(function(d) {{ return d.id; }}).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    var link = svg.append("g")
        .attr("class", "links")
      .selectAll("line")
      .data(graph.links)
      .enter().append("line")
        .attr("class", "link")
        .attr("stroke-width", 1.5);

    var node = svg.append("g")
        .attr("class", "nodes")
      .selectAll("circle")
      .data(graph.nodes)
      .enter().append("circle")
        .attr("r", 8)
        .attr("fill", function(d) {{ return d.type === "config" ? "#f39c12" : "#3498db"; }})
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    var text = svg.append("g")
        .attr("class", "labels")
      .selectAll("text")
      .data(graph.nodes)
      .enter().append("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(function(d) {{ return d.label; }});

    simulation
        .nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);

    function ticked() {{
      link
          .attr("x1", function(d) {{ return d.source.x; }})
          .attr("y1", function(d) {{ return d.source.y; }})
          .attr("x2", function(d) {{ return d.target.x; }})
          .attr("y2", function(d) {{ return d.target.y; }});

      node
          .attr("cx", function(d) {{ return d.x; }})
          .attr("cy", function(d) {{ return d.y; }});

      text
          .attr("x", function(d) {{ return d.x; }})
          .attr("y", function(d) {{ return d.y; }});
    }}

    function dragstarted(d) {{
      if (!d3.event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }}

    function dragged(d) {{
      d.fx = d3.event.x;
      d.fy = d3.event.y;
    }}

    function dragended(d) {{
      if (!d3.event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }}
  </script>
</body>
</html>
"""
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"D3 HTML visualization written to {output_html}")

def main():
    # Interactive dialogue
    project_path = input("Enter the path to your project folder: ").strip()
    if not os.path.isdir(project_path):
        print("The provided path does not exist or is not a directory.")
        return
    print(f"Outputs will be saved in the project folder: {project_path}")
    
    base_name = input("Enter a base file name for outputs (without extension): ").strip()
    # Generate output file names.
    json_output = os.path.join(project_path, f"{base_name}_ai.json")
    mermaid_output = os.path.join(project_path, f"{base_name}_mermaid.mmd")
    d3_output = os.path.join(project_path, f"{base_name}_d3.html")
    
    ignore_dirs_input = input("Enter comma-separated directory names to ignore (or leave blank): ").strip()
    if ignore_dirs_input:
        for d in ignore_dirs_input.split(","):
            ADDITIONAL_IGNORE_DIRS.add(d.strip())
    
    # Build the mapping.
    directory_tree = build_directory_tree(project_path)
    dependency_graph, internal_modules = build_dependency_graph(project_path, directory_tree)
    declared_libs = read_requirements(project_path)
    used_libs = aggregate_external_usage(dependency_graph)
    missing_declaration = list(used_libs - declared_libs)
    unused_declaration = list(declared_libs - used_libs)
    
    report = {
        "directory_tree": directory_tree,
        "dependency_
