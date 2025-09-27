from dataclasses import dataclass
import os
import ast
import json
import random
import pymunk
import networkx as nx
from typing import Dict, Tuple
from .physics import LAYOUT_ITERATION, LAYOUT_SCALE, SPRING_ITERATION, STIFFNESS
from typing_extensions import List, Optional
from networkx.readwrite import json_graph
from helpers.utils import get_app_support_directory
from networkx.classes.digraph import DiGraph
from .transversal import ImportsInfo, ConditionalTracker, DependencyNode


def find_imports(file_path: str, project_path: str) -> List[ImportsInfo]:
    """Finds all the imports in the file path"""
    with open(file_path, encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)
        conditional_imports = ConditionalTracker(project_path, file_path)
        conditional_imports.visit(tree)
        import_statements = conditional_imports.import_statements
    return import_statements


def iterate_over_files(
    file_path: str, project_path: str
) -> tuple[DependencyNode, dict]:
    # for storing nodes map
    nodes_map = {}

    # for storing if the node is visited or not
    visited = set()

    packages_queue = [(file_path, 0)]

    levels = {}

    file_imports = {}

    root_node = DependencyNode(name=os.path.basename(file_path), path=file_path)
    nodes_map[file_path] = root_node

    while packages_queue:
        current_file, current_level = packages_queue.pop(0)

        if current_file in visited:
            continue
        visited.add(current_file)

        levels[current_file] = current_level

        current_node = nodes_map[current_file]

        imports = find_imports(current_file, project_path)
        file_imports[current_file] = imports
        for module in imports:
            if module.path and os.path.isfile(module.path):
                child_path = module.path
                child_node = nodes_map.get(child_path)

                if not child_node:
                    child_node = DependencyNode(
                        name=os.path.basename(child_path), path=child_path
                    )
                    nodes_map[child_path] = child_node

                current_node.add_dependency(child_node)
                packages_queue.append((module.path, current_level + 1))

    return root_node, levels


def create_network_data(root_node: DependencyNode):
    """for creating networkx graph"""
    G = nx.DiGraph()

    queue = [root_node]
    visited_path = {root_node}

    while queue:
        current_node = queue.pop(0)

        G.add_node(current_node)

        for child_node in current_node.dependencies:
            G.add_edge(current_node, child_node)

            if child_node not in visited_path:
                queue.append(child_node)
                visited_path.add(child_node)

    return G


def tree_to_dict(node: Optional[DependencyNode]):
    """Recursively converts the dependency nodes to dict"""
    if not node:
        return

    return {
        "name": node.name,
        "path": node.path,
        "dependencies": [tree_to_dict(child) for child in node.dependencies],
    }


def dict_to_tree(data: Optional[dict]):
    """Recursively converts a dictionary back into a DependencyNode"""
    if not data:
        return

    # Create the parent node from the current dictionary level
    node = DependencyNode(name=data["name"], path=data["path"])

    # Recursively iterate and pray to god that it works
    for child_data in data["dependencies"]:
        child_node = dict_to_tree(child_data)
        if child_node:
            node.add_dependency(child_node)


def load_dependency_graph_data(
    file_path: str, project_path: str, file_name="dependency_graph.json"
) -> Tuple[DiGraph, Dict]:
    """Loads the dependency graph data from a JSON file, or creates it if not found."""
    support_dir = get_app_support_directory()
    path_of_storing_json = os.path.join(support_dir, file_name)
    layout = None
    # if file exists just fetch that no need to run the creating logic
    if os.path.exists(path_of_storing_json):
        with open(path_of_storing_json, "r") as file:
            data = json.load(file)

        G = json_graph.node_link_graph(data["data"])
        levels = data["levels"]

    # if file is not present we will have to call the other functions
    else:
        # Pass the file from core
        G, levels = create_network_data(file_path, project_path)
        _data = json_graph.node_link_data(G)
        data = {"data": _data, "levels": levels}
        with open(path_of_storing_json, "w") as f:
            json.dump(data, f)

    # Generating a layout for G
    layout = generate_shell_layout_from_levels(G, levels)

    return G, layout


def generate_layout(graph: nx.DiGraph, levels: dict, spring_iteration=SPRING_ITERATION):
    """Generate a layout in shell form and then changes it"""
    pass


def generate_shell_layout_from_levels(graph: nx.DiGraph, levels: dict) -> dict:
    """Generate a concentric shell layout"""

    nodes_by_level = {}
    center = None
    for node, level in levels.items():
        if level == 0:
            center = node
        if level not in list(nodes_by_level.keys()):
            nodes_by_level[level] = []
        nodes_by_level[level].append(node)

    shell_list = [nodes for level, nodes in sorted(nodes_by_level.items())]

    positions = nx.shell_layout(graph, nlist=shell_list, scale=LAYOUT_SCALE)
    return positions


if __name__ == "__main__":
    # dependency_graph = find_imports("components/library/core.py")
    graph = create_network_data("main.py", ".")
    print(graph)
    pass
