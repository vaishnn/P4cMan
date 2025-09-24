import ast
import os
from dataclasses import dataclass
from enum import Enum
from typing_extensions import List

EXCLUDE_DIRS: set

class ModuleType(Enum):
    LOCAL = "local"
    THIRD_PARTY = "third_party"
    BUILTIN = "builtin"

@dataclass(frozen=True)
class ImportsInfo:
    """For storing import data for visualizer"""
    name: str = ""
    parent: str = ""
    path: str = ""
    module_type: ModuleType = ModuleType.LOCAL
    import_line: int = 0
    is_conditional: bool = False
    alias: str = ""
    hash: str = ""

class DependencyNode:
    """Represents a node in the dependency graph."""
    def __init__(self, name: str, path: str):
        self._name = name
        self._path = path
        self._dependencies = []
        self._dependents = []

    @property
    def name(self):
        return self._name
    @property
    def path(self):
        return self._path
    @property
    def dependencies(self):
        return self._dependencies
    @property
    def dependents(self):
        return self._dependents

    def add_dependency(
        self,
        name: str = "",
        parent: str = "",
        path: str = "",
        module_type: ModuleType = ModuleType.LOCAL,
        import_line: int = 0,
        is_conditional: bool = False,
        alias: str = ""
    ):
        import_info = ImportsInfo(
            path = path,
            parent = parent,
            name = name,
            module_type = module_type,
            import_line = import_line,
            is_conditional = is_conditional,
            alias = alias

        )
        self._dependencies.append(import_info)

    def add_dependent(
        self,
        name: str = "",
        parent: str = "",
        path: str = "",
        module_type: ModuleType = ModuleType.LOCAL,
        import_line: int = 0,
        is_conditional: bool = False,
        alias: str = ""
    ):
        import_info = ImportsInfo(
            path = path,
            name = name,
            parent = parent,
            module_type = module_type,
            import_line = import_line,
            is_conditional = is_conditional,
            alias = alias
        )
        self._dependents.append(import_info)

class ConditionalTracker(ast.NodeVisitor):
    """for iterating over nodes and collecting the information"""
    def __init__(self, project_path: str, base_file: str):
        self.project_path = project_path
        self.base_file = base_file
        self._in_condition = False
        self.import_statements = []

    def visit_If(self, node):
        old_state = self._in_condition
        self._in_condition = True
        self.generic_visit(node)
        self._in_condition = old_state

    def resolve_imports(self, module_name):
        """Resolve the relative imports and find the path of the imported stuff"""
        module_type = ModuleType.LOCAL
        if module_name.startswith('.'):
            level = 0
            while module_name[level] == ".":
                level += 1

            base_path = os.path.dirname(os.path.abspath(self.base_file))
            file_path_parts = self.base_file.split(os.sep)
            if level > 1:
                base_path = os.sep.join(file_path_parts[:-(level-1)])

            # Omitting the inital '.' and split into seperate parts
            module_path_parts = module_name[level:].split(".")
            candidate_path = os.path.join(base_path, *module_path_parts)
        else:
            module_path_parts = module_name.split(".")
            candidate_path = os.path.join(self.project_path, *module_path_parts)
        if not (os.path.exists(candidate_path) or os.path.isfile(candidate_path+".py")):
            module_type = ModuleType.BUILTIN
            path = ""
            return path, module_type
        return candidate_path, module_type



    def visit_Import(self, node):
        module_type = ModuleType.LOCAL
        for name in node.names:
            alias_name = name.asname if name.asname else ""

            path = os.path.join(self.project_path, name.name)
            if not (os.path.exists(path) or os.path.isfile(path+".py")):
                    # It can be externallu installed as well that can be checked by PIP inspect
                module_type = ModuleType.BUILTIN
                path = ""

            if os.path.isdir(path):
                if os.path.isfile(os.sep.join([path, name.name + '.py'])):
                    path = os.sep.join([path, name.name + '.py'])
            elif os.path.isfile(path+'.py'):
                path = path+'.py'

            self.import_statements.append(ImportsInfo(
                name=name.name,
                import_line=name.lineno,
                module_type=module_type,
                path=path,
                alias=alias_name,
                is_conditional=self._in_condition
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module if node.module else ""
        path, module_type =self.resolve_imports(node.level*'.' + module)

        if not (os.path.exists(path) or os.path.isfile(path+".py")):
                # It can be externallu installed as well that can be checked by PIP inspect
            module_type = ModuleType.BUILTIN
            path = ""
        for name in node.names:
            alias_name = name.asname if name.asname else ""
            if os.path.isdir(path):
                if os.path.isfile(os.sep.join([path, name.name + '.py'])):
                    path = os.sep.join([path, name.name + '.py'])
            elif os.path.isfile(path+'.py'):
                path = path+'.py'
            self.import_statements.append(
                ImportsInfo(
                    name=name.name,
                    parent = os.path.relpath(path, self.project_path) if path else "",
                    import_line=name.lineno,
                    path = path,
                    alias=alias_name,
                    module_type=module_type,
                    is_conditional=self._in_condition
                )
            )

def find_imports(file_path: str, project_path: str) -> List[ImportsInfo]:
    """Finds all the imports in the file path"""
    with open(file_path, encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=file_path)
        conditional_imports = ConditionalTracker(project_path, file_path)
        conditional_imports.visit(tree)
        import_statements = conditional_imports.import_statements
        return import_statements

def iterate_over_files(project_path: str, file_path: str):
    graph = {}
    visited = set()
    packages_queue = [file_path]
    while packages_queue:
        current_file = packages_queue.pop(0)

        # if current_file in visited:
        #     continue

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

def build_dependency_tree(start_file, project_root):
    """Build a dependency graph starting from an entry point file"""

    graph = iterate_over_files(project_root, start_file)

    for keys, values in graph.items():
        print(keys)
        print(values)

        break


if __name__ == "__main__":
    # dependency_graph = find_imports("components/library/core.py")
    project_path = os.path.abspath(".")
    file_name = os.path.abspath("main.py")
    file_path = os.path.join(project_path, file_name)
    dependency_graph = build_dependency_tree(file_name, project_path)
