from collections import defaultdict, deque
import json
from typing import Dict, List, Set, Deque, TextIO
from sys import stdout


METADATA_FILE: str = "metadata.json"
RING_0_16_20_ID: str = (
    "registry+https://github.com/rust-lang/crates.io-index#ring@0.16.20"
)

with open(METADATA_FILE, "rb") as f:
    metadata = json.load(f)

mapping_id2index: Dict[str, int] = dict()
mapping_index2id: List[str] = list()
reversed_dependencies: Dict[int, Set[int]] = defaultdict(set)


def crate_id_2_index(crate_id: str) -> int:
    len_crates: int = len(mapping_id2index)
    if crate_id not in mapping_id2index:
        mapping_id2index[crate_id] = len_crates
        mapping_index2id.append(crate_id)
        return len_crates
    else:
        return mapping_id2index[crate_id]


for meta_node in metadata["resolve"]["nodes"]:
    crate_id: str = meta_node["id"]
    crate_index: int = crate_id_2_index(crate_id)
    crate_deps: List[str] = meta_node["dependencies"]
    for each in crate_deps:
        dep_index: int = crate_id_2_index(each)
        reversed_dependencies[dep_index].add(crate_index)

ring_0_16_20_index: int = crate_id_2_index(RING_0_16_20_ID)
sub_tree: Dict[int, Set[int]] = dict()
queue: Deque[int] = deque()
queue.append(ring_0_16_20_index)
while queue:
    cur_crate_index: int = queue.popleft()
    cur_reversed_deps: Set[int] = reversed_dependencies[cur_crate_index]
    sub_tree[cur_crate_index] = cur_reversed_deps
    for each in cur_reversed_deps:
        queue.append(each)


def make_space(depth: int, text: str, output_io: TextIO):
    print(" " * (depth * 2) + text, file=output_io)


del queue

crate_visited: Set[int] = set()


def dfs(crate_index: int, depth: int, output_io: TextIO):
    global mapping_id2index, sub_tree, crate_visited
    sub_part = sub_tree[crate_index]
    if crate_index in crate_visited:
        make_space(depth, f"{mapping_index2id[crate_index]} {{ ... }}", output_io)
        return
    crate_visited.add(crate_index)
    if sub_part:
        make_space(depth, f"{mapping_index2id[crate_index]} {{", output_io)
        for each in sub_tree[crate_index]:
            dfs(each, depth + 1, output_io)
        make_space(depth, "}", output_io)
    else:
        make_space(depth, f"{mapping_index2id[crate_index]} {{}}", output_io)


with open("reversed_tree_ring.txt", "w", encoding="utf-8") as f:
    dfs(ring_0_16_20_index, 0, f)
