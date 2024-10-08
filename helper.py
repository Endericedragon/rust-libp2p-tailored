import graphviz
import json


class Package:
    __slots__ = ("name", "version", "id", "manifest_path", "dependencies")

    def __init__(self, name: str, version: str, manifest_path: str) -> None:
        self.name: str = name
        self.version: str = version
        self.manifest_path: str = manifest_path
        self.dependencies: set["Package"] = set()

    def __hash__(self) -> int:
        return hash(self.id)


def json_id_to_dot_id(json_id: str) -> str:
    return json_id.rsplit("#")[-1]


with open("metadata.json", "rb") as f:
    data = json.load(f)

dot = graphviz.Digraph("dependency-graph", comment="Dependency Graph of This Crate")

workspace_members: set[str] = set(data["workspace_members"])
pacakges_wsm: list[dict] = list(filter(lambda x: x["id"] in workspace_members, data["packages"]))
for each in pacakges_wsm:
    dot.node(json_id_to_dot_id(each["id"]), each["name"])

packages_wsm_map: dict[str, Package] = {
    each["id"]: Package(each["name"], each["version"], each["manifest_path"])
    for each in pacakges_wsm
}

for node in data["resolve"]["nodes"]:
    node_id = node["id"]
    node_deps = node["dependencies"]
    if node_id not in packages_wsm_map:
        continue
    for dep in node_deps:
        if dep in packages_wsm_map:
            dot.edge(json_id_to_dot_id(node_id), json_id_to_dot_id(dep))
            packages_wsm_map[node_id].dependencies.add(dep)

with open("dependency-graph.dot", "w") as f:
    f.write(dot.source)
