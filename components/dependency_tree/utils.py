import ast
import os
from networkx.classes.digraph import DiGraph
from typing_extensions import List
from .transversal import ImportsInfo, ConditionalTracker
import networkx as nx
from networkx.readwrite import json_graph
from helpers.utils import get_app_support_directory
import json


def find_imports(file_path: str, project_path: str) -> List[ImportsInfo]:
    """Finds all the imports in the file path"""
    with open(file_path, encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)
        conditional_imports = ConditionalTracker(project_path, file_path)
        conditional_imports.visit(tree)
        import_statements = conditional_imports.import_statements
        return import_statements


def iterate_over_files(project_path: str, file_path: str) -> dict:
    graph = {}
    visited = set()
    packages_queue = [file_path]
    while packages_queue:
        current_file = packages_queue.pop(0)

        if current_file in visited:
            continue

        visited.add(current_file)
        imports = find_imports(current_file, project_path)

        for module in imports:
            try:
                graph[current_file].append(module)
            except KeyError:
                graph[current_file] = [module]

            if module.path != "":
                if os.path.isfile(module.path):
                    packages_queue.append(module.path)

    return graph


def build_dependency_tree(start_file: str, project_root: str):
    """Build a dependency graph starting from an entry point file"""

    graph = iterate_over_files(project_root, start_file)

    for keys, values in graph.items():
        print(keys)
        print(values)

        break


def create_network_data(python_file_path: str):
    """for creating networkx graph"""

    # Just creating a placeholder for graph
    G = nx.DiGraph()
    G.add_edge("a", "b")
    G.add_edge("b", "c")
    G.add_edge("a", "d")

    return G


def load_dependency_graph_data(
    python_file_path: str, file_name="dependency_graph.json"
) -> DiGraph:
    """Loads the dependency graph data from a JSON file, or creates it if not found."""
    support_dir = get_app_support_directory()
    path_of_storing_json = os.path.join(support_dir)

    # if file exists just fetch that no need to run the creating logic
    if os.path.exists(path_of_storing_json):
        with open(path_of_storing_json, "r") as file:
            data = json.load(file)

        G = json_graph.node_link_data(data)

    # if file is not present we will have to call the other functions
    else:
        # Pass the file from core
        G = create_network_data("some_place_holder_path")
        data = json_graph.node_link_data(G)
        with open(path_of_storing_json, "w") as f:
            json.dump(data, f)

    return G


if __name__ == "__main__":
    # dependency_graph = find_imports("components/library/core.py")
    project_path = os.path.abspath(".")
    file_name = os.path.abspath("main.py")
    file_path = os.path.join(project_path, file_name)
    dependency_graph = build_dependency_tree(file_name, project_path)
