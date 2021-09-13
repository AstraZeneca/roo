import collections
from typing import List, cast, Iterable, Any

from .dependencies import (
    RootDependency, ResolvedDependency, AnyDependency, UnresolvedDependency)


def traverse_breadth_first_layered(
        base: AnyDependency) -> List[List[AnyDependency]]:
    """
    Performs a breadth first traversal of the dependency tree.
    It returns every layer of the breadth first as an independent list,
    hence the return being a list of lists, ordered from top to bottom.

    """
    layers: List[List[AnyDependency]] = [[base]]
    while True:
        layer = layers[-1]
        sublayer: List[AnyDependency] = []
        for node in layer:
            if not isinstance(node, UnresolvedDependency):
                sublayer.extend(node.dependencies)
        if len(sublayer) == 0:
            break
        layers.append(sublayer)

    return layers


def traverse_depth_first(base: AnyDependency) -> List[AnyDependency]:
    """Performs a depth first traversal of the dependency tree.
    """
    def _traverse_tree_2(base: AnyDependency) -> List[AnyDependency]:
        queue: List[AnyDependency] = []
        current_idx = 0
        queue.append(base)
        while len(queue) != current_idx:
            node = queue[current_idx]
            if not isinstance(node, UnresolvedDependency):
                queue.extend(cast(Iterable, node.dependencies))
            current_idx += 1
        return queue

    deps = _traverse_tree_2(base)

    return deps


def traverse_depth_first_unique(
        base: AnyDependency) -> List[AnyDependency]:
    """Performs a depth first traversal of the dependency tree,
    but ensure that a dependency is added only the first time, and not
    more.
    """
    return _unique(traverse_depth_first(base))


def _unique(resolved_deps: List[AnyDependency]) -> List[AnyDependency]:
    od: Any = collections.OrderedDict()
    for dep in resolved_deps:
        if isinstance(dep, RootDependency):
            od[""] = dep
        elif isinstance(dep, ResolvedDependency):
            if dep.name in od:
                continue
            od[dep.name] = dep
        else:
            raise TypeError(f"Unable to handle {dep}")

    return list(od.values())
