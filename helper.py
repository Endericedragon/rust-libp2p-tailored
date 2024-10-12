import json
import sys
from collections import deque

import graphviz


class Package:
    """
    代表Metadata中`packages`数组中的一项。
    """

    __slots__ = (
        "name",
        "version",
        "id",
        "manifest_path",
        "dependencies",
        "parent_dependencies",
        "real_parent_count",
        "real_dep_count",
        "ranking",
    )

    def __init__(self, name: str, version: str, _id: str, manifest_path: str) -> None:
        self.name: str = name
        self.version: str = version
        self.id: str = _id
        self.manifest_path: str = manifest_path
        self.dependencies: set[str] = set()
        self.parent_dependencies: set[str] = set()
        # real表示真实数量，因为上述两个set只会包含workspace members中的项，
        # 因此数量上会比下列两个变量记录的少
        self.real_parent_count: int = 0
        self.real_dep_count: int = 0
        self.ranking: float = 0.0

    def __hash__(self) -> int:
        return hash(self.id)


def json_id_to_dot_id(json_id: str) -> str:
    """
    不能用诸如"path+file:///..."作为dot图中的节点ID，故使用最后一节的部分作为替代。
    """
    sharp_idx = json_id.rfind("#")
    if sharp_idx == -1 or json_id[sharp_idx + 1].isdigit():
        return json_id.rsplit("/")[-1]
    return json_id.rsplit("#")[-1]


# 从`cargo metadata`中加载metadata，并创建依赖图（graphviz对象）
with open("metadata.json", "rb") as f:
    data = json.load(f)
dot = graphviz.Digraph("dependency-graph", comment="Dependency Graph of This Crate")

# 将所有workspace members作为节点加入依赖图中
workspace_members: set[str] = set(data["workspace_members"])
workspace_member_info: list[dict] = list(
    filter(lambda x: x["id"] in workspace_members, data["packages"])
)
for each in workspace_member_info:
    dot.node(json_id_to_dot_id(each["id"]))

# 构造从ID到Package对象的映射关系
workspace_member_packages: dict[str, Package] = {
    each["id"]: Package(
        each["name"], each["version"], each["id"], each["manifest_path"]
    )
    for each in workspace_member_info
}

# 分析依赖关系，并以有向边的形式，加入到依赖图中
for node in data["resolve"]["nodes"]:
    node_id: str = node["id"]
    node_deps: list[dict] = node["deps"]
    # only consider workspace members
    if node_id not in workspace_member_packages:
        continue
    for dep_info in node_deps:
        dep_id: str = dep_info["pkg"]
        dep_kinds: list[dict] = dep_info["dep_kinds"]

        # 仅考虑普通的`dependencies`，不考虑dev-dependencies
        if any(filter(lambda x: x["kind"] is None, dep_kinds)):  # type: ignore
            workspace_member_packages[node_id].real_dep_count += 1
            if dep_id in workspace_member_packages:
                dot.edge(json_id_to_dot_id(node_id), json_id_to_dot_id(dep_id))
                workspace_member_packages[node_id].dependencies.add(dep_id)
                workspace_member_packages[dep_id].parent_dependencies.add(node_id)
                workspace_member_packages[dep_id].real_parent_count += 1


workspace_member_packages_sorted: list[Package] = sorted(
    list(workspace_member_packages.values()),
    key=lambda x: len(x.dependencies),
    reverse=True,
)

with open("dependency-graph.dot", "w") as f:
    f.write(dot.source)

# 对所有节点进行拓扑排序
queue: deque[Package] = deque(
    [v for v in workspace_member_packages.values() if len(v.dependencies) == 0]
)
topological_sorted_packages: list[Package] = []
while queue:
    package = queue.popleft()
    topological_sorted_packages.append(package)
    for parent_id in package.parent_dependencies:
        parent_package = workspace_member_packages[parent_id]
        parent_package.dependencies.remove(package.id)
        if len(parent_package.dependencies) == 0:
            queue.append(parent_package)
    workspace_member_packages.pop(package.id)

if len(topological_sorted_packages) != len(workspace_member_packages_sorted):
    print("Error: topological sort failed", file=sys.stderr)
    exit(1)

# 输出结果
for i, each in enumerate(topological_sorted_packages):
    # 父依赖项越多(parent_count越大)，说明在依赖树中越接近“核心”
    # 依赖项越少(dep_count越小)，拓扑顺序越靠前(i越小)，说明处理难度越低
    # 此时我们希望rank的值越小，这样才越容易被排在前面
    # 为防止除零错误，我们加上1
    each.ranking = (each.real_dep_count + i + 1) / (each.real_parent_count + 1)
    # display_name = json_id_to_dot_id(each.id)
    # print(
    #     f"{display_name} [ deps: {each.real_dep_count}, parent: {each.real_parent_count}, rank: {each.ranking:.3f} ]",
    #     file=f,
    # )

rank_sorted_packages = sorted(topological_sorted_packages, key=lambda x: x.ranking)

sorted_results: dict[str, list[str]] = {
    "topological_sorted_packages": [
        f"{json_id_to_dot_id(each.id)} [ deps: {each.real_dep_count}, parent: {each.real_parent_count}, rank: {each.ranking:.3f} ]"
        for each in topological_sorted_packages
    ],
    "comprehensive_sorted_packages": [
        f"{json_id_to_dot_id(each.id)} [ deps: {each.real_dep_count}, parent: {each.real_parent_count}, rank: {each.ranking:.3f} ]"
        for each in rank_sorted_packages
    ],
}

# for each in rank_sorted_packages:
#     display_name = json_id_to_dot_id(each.id)
#     print(
#         f"{display_name} [ deps: {each.real_dep_count}, parent: {each.real_parent_count}, rank: {each.ranking:.3f} ]",
#         file=f,
#     )

with open("sort_result.json", "w") as f:
    json.dump(sorted_results, f, indent=4)
