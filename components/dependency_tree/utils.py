import os
import ast
import json
import random
import pymunk
import networkx as nx
from typing import Dict, Tuple
from typing_extensions import List
from networkx.readwrite import json_graph
from helpers.utils import get_app_support_directory
from networkx.classes.digraph import DiGraph
from .transversal import ImportsInfo, ConditionalTracker


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
) -> Tuple[DiGraph, Dict]:
    """Loads the dependency graph data from a JSON file, or creates it if not found."""
    support_dir = get_app_support_directory()
    path_of_storing_json = os.path.join(support_dir, file_name)

    # if file exists just fetch that no need to run the creating logic
    if os.path.exists(path_of_storing_json):
        with open(path_of_storing_json, "r") as file:
            data = json.load(file)

        G = json_graph.node_link_graph(data)

    # if file is not present we will have to call the other functions
    else:
        # Pass the file from core
        G = create_network_data("some_place_holder_path")
        data = json_graph.node_link_data(G)
        with open(path_of_storing_json, "w") as f:
            json.dump(data, f)

    # Generating a layout for G
    layout = generate_layout(G)
    return G, layout


def generate_layout(
    graph: DiGraph, iteration=1000, repulsion_strenght=5000, spring_stiffness=50
) -> dict:
    """Generate layout setup using pymunk engine"""

    # pymunk space
    space = pymunk.Space()
    space.damping = 0.6

    # dictionaries for bodies
    bodies = {}

    # Create a pymunk body for each node
    for node in graph.nodes():
        body = pymunk.Body(mass=1, moment=float("inf"))

        # Start nodes at random locations
        body.position = (random.uniform(-50, 50), random.uniform(-50, 50))

        # Giving shape for the collision
        shape = pymunk.Circle(body, radius=5)
        space.add(body, shape)
        bodies[node] = body

    for u, v in graph.edges():
        spring = pymunk.DampedSpring(
            a=bodies[u],
            b=bodies[v],
            rest_length=50,
            anchor_a=(0, 0),
            anchor_b=(0, 0),
            stiffness=spring_stiffness,
            damping=10,
        )

        space.add(spring)

    # Run the simulation
    for i in range(iteration):
        for node1 in graph.nodes():
            for node2 in graph.nodes():
                # Skipping simulation
                if node1 == node2:
                    continue

                # assigning bodies
                body1 = bodies[node1]
                body2 = bodies[node2]

                # Calculation direction and distance
                direction = body2.position - body1.position
                distance = direction.length

                # Avoid division by zero
                if distance < 1:
                    distance = 1

                # Calculate the resulting force
                force_magnitude = repulsion_strenght / (distance + distance)

                # Apply force
                force_vector = direction.normalized() * force_magnitude
                body1.apply_force_at_local_point(-force_vector, (0, 0))
                body2.apply_force_at_local_point(force_vector, (0, 0))

        space.step(1 / 60)

    return {node: body.position for node, body in bodies.items()}


if __name__ == "__main__":
    # dependency_graph = find_imports("components/library/core.py")
    project_path = os.path.abspath(".")
    file_name = os.path.abspath("main.py")
    file_path = os.path.join(project_path, file_name)
    dependency_graph = build_dependency_tree(file_name, project_path)
