import os
import ast
import json
import networkx as nx
from typing_extensions import List, Optional
from helpers.utils import get_app_support_directory
from .transversal import ImportsInfo, ConditionalTracker, DependencyNode


def find_imports(file_path: str, project_path: str) -> List[ImportsInfo]:
    """Finds all the imports in the file path"""
    with open(file_path, encoding="utf-8") as file:
        # parse by ast and pass to the transversal class
        tree = ast.parse(file.read(), filename=file_path)
        conditional_imports = ConditionalTracker(project_path, file_path)
        conditional_imports.visit(tree)
        import_statements = conditional_imports.import_statements
    return import_statements


def create_dependency_node(file_path: str, project_path: str) -> DependencyNode:
    # for storing nodes map
    nodes_map = {}

    # for storing if the node is visited or not
    visited = set()

    # for BFS
    packages_queue = [(file_path, 0)]

    # for informations of imports
    file_imports = {}

    # saving all the nodes here and nodes_map
    root_node = DependencyNode(name=os.path.basename(file_path), path=file_path)
    nodes_map[file_path] = root_node

    while packages_queue:
        current_file, current_level = packages_queue.pop(0)

        if current_file in visited:
            continue
        visited.add(current_file)

        current_node = nodes_map[current_file]

        imports = find_imports(current_file, project_path)
        file_imports[current_file] = imports
        for module in imports:
            # In the case if find_imports gave wrong path
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

    return root_node


def create_network_data(node: DependencyNode):
    """for creating networkx graph"""
    G = nx.DiGraph()
    queue = [node]
    visited_path = {node}

    while queue:
        current_node = queue.pop(0)

        if current_node not in visited_path:
            G.add_node(current_node.path)

        for child_node in current_node.dependencies:
            G.add_edge(current_node.path, child_node.path)

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

    return node


def create_file_dependency(
    file_path: str, project_folder: str, path_of_storing_json: str
):
    """Loads and creates a JSON for dependency Node"""

    node = create_dependency_node(file_path, project_folder)

    G = create_network_data(node)
    layout = generate_shell_layout(G, node)

    # convert the tree to dict
    node_dict = tree_to_dict(node)
    with open(path_of_storing_json, "w") as file:
        json.dump(node_dict, file)

    return G, layout


def load_file_dependency(path_of_storing_json: str):
    """load file dependency from saved JSON file"""
    with open(path_of_storing_json, "r") as file:
        data = json.load(file)

    node = dict_to_tree(data)

    if node is None:
        return None, None

    G = create_network_data(node)
    # layout = nx.layout.fruchterman_reingold_layout(G)
    layout = generate_shell_layout(G, node)

    return G, layout


def load_dependency_graph_data(
    file_path: str, project_path: str, file_name="dependency_graph.json"
):
    """Loads the dependency graph data from a JSON file, or creates it if not found."""
    support_dir = get_app_support_directory()
    path_of_storing_json = os.path.join(support_dir, file_name)

    # if os.path.exists(path_of_storing_json):
    #     G, layout = load_file_dependency(path_of_storing_json)

    # else:
    # Pass the file from core
    G, layout = create_file_dependency(file_path, project_path, path_of_storing_json)

    return (G, layout)


def generate_shell_layout(G: nx.DiGraph, node: DependencyNode) -> dict:
    """Generate a concentric shell layout"""

    levels = nx.shortest_path_length(G, source=node.path)
    nodes_by_level = {}
    for node_id, level in levels.items():
        if level not in nodes_by_level:
            nodes_by_level[level] = []
        nodes_by_level[level].append(node_id)

    # This is the list we pass to networkx
    shell_list = [nodes for level, nodes in sorted(nodes_by_level.items())]
    positions = nx.shell_layout(G, nlist=shell_list, scale=5000)
    return positions


if __name__ == "__main__":
    # dependency_graph = find_imports("components/library/core.py")
    pass
