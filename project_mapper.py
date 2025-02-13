#!/usr/bin/env python3
"""
Project Mapper: Create a mapping of your Python project’s functions, classes, and interdependencies.
Outputs a JSON file and (optionally) a Mermaid diagram file.
Supports two Mermaid modes: "full" (detailed, including function calls) and "summary" (high-level).
"""

import os
import ast
import json
import argparse


class FunctionCallVisitor(ast.NodeVisitor):
    """
    AST visitor to capture function calls within a function or method.
    """
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        func_name = self.get_called_name(node.func)
        if func_name:
            self.calls.append({
                "name": func_name,
                "lineno": node.lineno
            })
        self.generic_visit(node)

    def get_called_name(self, node):
        """
        Attempt to extract a dotted name from the call node.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        return None


def parse_functions_and_classes(file_path):
    """
    Parse a Python file and return a dictionary with its functions and classes.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None

    module_data = {
        "file": file_path,
        "functions": [],
        "classes": []
    }

    # Process top-level definitions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            func_data = {
                "name": node.name,
                "lineno": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node),
                "calls": []
            }
            visitor = FunctionCallVisitor()
            visitor.visit(node)
            func_data["calls"] = visitor.calls
            module_data["functions"].append(func_data)
        elif isinstance(node, ast.ClassDef):
            class_data = {
                "name": node.name,
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node),
                "methods": []
            }
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef):
                    method_data = {
                        "name": subnode.name,
                        "lineno": subnode.lineno,
                        "args": [arg.arg for arg in subnode.args.args],
                        "docstring": ast.get_docstring(subnode),
                        "calls": []
                    }
                    visitor = FunctionCallVisitor()
                    visitor.visit(subnode)
                    method_data["calls"] = visitor.calls
                    class_data["methods"].append(method_data)
            module_data["classes"].append(class_data)

    return module_data


def generate_mermaid(project_data, mode="full"):
    """
    Generate Mermaid code (graph TD) from the project mapping.
    
    Parameters:
      - project_data: the JSON mapping of the project.
      - mode: "full" for detailed view (including function calls)
              "summary" for a high-level view (modules, functions, classes, methods only)
    """
    lines = ["graph TD"]
    node_id = 0
    node_map = {}  # Map to keep track of assigned node IDs

    def get_node_id():
        nonlocal node_id
        nid = f"node{node_id}"
        node_id += 1
        return nid

    # Iterate through modules
    for module in project_data["modules"]:
        mod_id = get_node_id()
        node_map[module["file"]] = mod_id
        mod_label = f"Module: {os.path.basename(module['file'])}"
        lines.append(f'{mod_id}["{mod_label}"]')

        # Top-level functions
        for func in module["functions"]:
            func_key = f'{module["file"]}::{func["name"]}'
            func_id = get_node_id()
            node_map[func_key] = func_id
            lines.append(f'{func_id}["Function: {func["name"]}"]')
            lines.append(f"{mod_id} --> {func_id}")
            if mode == "full":
                # Edges for function calls
                for call in func["calls"]:
                    call_key = f'call::{func_key}::{call["name"]}::{call["lineno"]}'
                    if call_key not in node_map:
                        call_id = get_node_id()
                        node_map[call_key] = call_id
                        call_label = f'Call: {call["name"]} (line {call["lineno"]})'
                        lines.append(f'{call_id}["{call_label}"]')
                    else:
                        call_id = node_map[call_key]
                    lines.append(f"{func_id} --> {call_id}")

        # Classes and their methods
        for cls in module["classes"]:
            cls_key = f'{module["file"]}::class::{cls["name"]}'
            cls_id = get_node_id()
            node_map[cls_key] = cls_id
            lines.append(f'{cls_id}["Class: {cls["name"]}"]')
            lines.append(f"{mod_id} --> {cls_id}")
            for method in cls["methods"]:
                meth_key = f'{cls_key}::{method["name"]}'
                meth_id = get_node_id()
                node_map[meth_key] = meth_id
                lines.append(f'{meth_id}["Method: {method["name"]}"]')
                lines.append(f"{cls_id} --> {meth_id}")
                if mode == "full":
                    for call in method["calls"]:
                        call_key = f'call::{meth_key}::{call["name"]}::{call["lineno"]}'
                        if call_key not in node_map:
                            call_id = get_node_id()
                            node_map[call_key] = call_id
                            call_label = f'Call: {call["name"]} (line {call["lineno"]})'
                            lines.append(f'{call_id}["{call_label}"]')
                        else:
                            call_id = node_map[call_key]
                        lines.append(f"{meth_id} --> {call_id}")

    return "\n".join(lines)


def main(root_dir, output_json, mermaid_file=None, mermaid_mode="full"):
    project_data = {"modules": []}
    # Walk through the directory recursively
    for subdir, dirs, files in os.walk(root_dir):
        # Exclude some directories (e.g. .git, __pycache__)
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__"]]
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(subdir, file)
                module_info = parse_functions_and_classes(file_path)
                if module_info is not None:
                    project_data["modules"].append(module_info)

    # Write the JSON mapping
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=4)
    print(f"JSON output written to {output_json}")

    # Optionally, write a Mermaid diagram representation
    if mermaid_file:
        mermaid_code = generate_mermaid(project_data, mode=mermaid_mode)
        with open(mermaid_file, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"Mermaid diagram output ({mermaid_mode} mode) written to {mermaid_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a mapping of Python project functions/classes and their call relationships."
    )
    parser.add_argument("root", help="Root directory of the project (e.g., the git repo root)")
    parser.add_argument(
        "-o",
        "--output",
        default="project_map.json",
        help="Output JSON file (default: project_map.json)"
    )
    parser.add_argument(
        "--mermaid",
        default=None,
        help="Optional output file for Mermaid diagram (e.g., project_map.mmd)"
    )
    parser.add_argument(
        "--mermaid-mode",
        choices=["full", "summary"],
        default="full",
        help="Mermaid diagram mode: 'full' for detailed view (includes function calls) or 'summary' for high-level view (default: full)"
    )
    args = parser.parse_args()
    main(args.root, args.output, args.mermaid, args.mermaid_mode)
