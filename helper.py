from collections import deque
import graphviz
import json


class Package:
    __slots__ = (
        "name",
        "version",
        "id",
        "manifest_path",
        "dependencies",
        "parent_dependencies",
    )

    def __init__(self, name: str, version: str, _id: str, manifest_path: str) -> None:
        self.name: str = name
        self.version: str = version
        self.id: str = _id
        self.manifest_path: str = manifest_path
        self.dependencies: set[str] = set()
        self.parent_dependencies: set[str] = set()

    def __hash__(self) -> int:
        return hash(self.id)


# things like "path+file:///..." cannot be used as node names in dot, so we need to extract the last part of the id
def json_id_to_dot_id(json_id: str) -> str:
    sharp_idx = json_id.rfind("#")
    if sharp_idx == -1 or json_id[sharp_idx + 1].isdigit():
        return json_id.rsplit("/")[-1]
    return json_id.rsplit("#")[-1]


# load metadata from `cargo metadata` outputs
with open("metadata.json", "rb") as f:
    data = json.load(f)
# create a graphviz object
dot = graphviz.Digraph("dependency-graph", comment="Dependency Graph of This Crate")

# add all workspace members as nodes
workspace_members: set[str] = set(data["workspace_members"])
pacakges_wsm: list[dict] = list(
    filter(lambda x: x["id"] in workspace_members, data["packages"])
)
for each in pacakges_wsm:
    dot.node(json_id_to_dot_id(each["id"]))
# create a map of packages, mapping from id to Package object
packages_wsm_map: dict[str, Package] = {
    each["id"]: Package(
        each["name"], each["version"], each["id"], each["manifest_path"]
    )
    for each in pacakges_wsm
}

for node in data["resolve"]["nodes"]:
    node_id = node["id"]
    node_deps = node["dependencies"]
    if node_id not in packages_wsm_map:
        continue
    for dep_id in node_deps:
        if dep_id in packages_wsm_map:
            dot.edge(json_id_to_dot_id(node_id), json_id_to_dot_id(dep_id))
            packages_wsm_map[node_id].dependencies.add(dep_id)
            packages_wsm_map[dep_id].parent_dependencies.add(node_id)

package_wsm_sorted: list[Package] = sorted(
    list(packages_wsm_map.values()), key=lambda x: len(x.dependencies), reverse=True
)

with open("dependency-graph.dot", "w") as f:
    f.write(dot.source)

# topology sort the packages
# dot_after = graphviz.Digraph("dependency-graph-after")
queue: deque[Package] = deque(
    [v for v in packages_wsm_map.values() if len(v.dependencies) == 0]
)
sorted_packages: list[Package] = []
while queue:
    package = queue.popleft()
    sorted_packages.append(package)
    for parent_id in package.parent_dependencies:
        parent_package = packages_wsm_map[parent_id]
        parent_package.dependencies.remove(package.id)
        if len(parent_package.dependencies) == 0:
            queue.append(parent_package)
    packages_wsm_map.pop(package.id)

# for each in packages_wsm_map.values():
#     dot_after.node(json_id_to_dot_id(each.id))
# for each in packages_wsm_map.values():
#     for dep_id in each.dependencies:
#         dot_after.edge(json_id_to_dot_id(each.id), json_id_to_dot_id(dep_id))
# with open("dependency-graph-after.dot", "w") as f:
#     f.write(dot_after.source)

for each in sorted_packages:
    print(f"{each.name}@{each.version}, ")

print()
for each in package_wsm_sorted:
    print(f"{each.name}@{each.version}, ")
