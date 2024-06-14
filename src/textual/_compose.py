from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import App
    from .widget import Widget


def compose(node: App | Widget) -> list[Widget]:
    """Compose child widgets.

    Args:
        node: The parent node.

    Returns:
        A list of widgets.
    """
    _rich_traceback_omit = True
    from .widget import MountError, Widget

    app = node.app
    nodes: list[Widget] = []
    compose_stack: list[Widget] = []
    composed: list[Widget] = []
    app._compose_stacks.append(compose_stack)
    app._composed.append(composed)
    iter_compose = iter(node.compose())
    is_generator = hasattr(iter_compose, "throw")
    try:
        while True:
            try:
                child = next(iter_compose)
            except StopIteration:
                break

            if not isinstance(child, Widget):
                mount_error = MountError(
                    f"Can't mount {type(child)}; expected a Widget instance."
                )
                if is_generator:
                    iter_compose.throw(mount_error)  # type: ignore
                else:
                    raise mount_error from None

            try:
                child.id
            except AttributeError:
                mount_error = MountError(
                    "Widget is missing an 'id' attribute; did you forget to call super().__init__()?"
                )
                if is_generator:
                    iter_compose.throw(mount_error)  # type: ignore
                else:
                    raise mount_error from None

            if composed:
                nodes.extend(composed)
                composed.clear()
            if compose_stack:
                try:
                    compose_stack[-1].compose_add_child(child)
                except Exception as error:
                    if is_generator:
                        # So the error is raised inside the generator
                        # This will generate a more sensible traceback for the dev
                        iter_compose.throw(error)  # type: ignore
                    else:
                        raise
            else:
                nodes.append(child)
        if composed:
            nodes.extend(composed)
            composed.clear()
    finally:
        app._compose_stacks.pop()
        app._composed.pop()
    return nodes


def recompose(node: App | Widget) -> tuple[list[Widget], set[Widget]]:
    """Recompose a node (nodes with a matching nodes will have their state copied).

    Args:
        Node to be recomposed.

    Returns:
        A list of new nodes, and a list of nodes to be removed.
    """
    children: list[Widget] = list(
        child for child in node.children if not child.has_class("-textual-system")
    )
    children_by_id = {child.id: child for child in children if child.id is not None}
    new_children: list[Widget] = []
    remove_children: set[Widget] = set(children)
    for node in compose(node):
        if node.id is None:
            new_children.append(node)
        else:
            if (existing_child := children_by_id.pop(node.id, None)) is not None:
                new_children.append(existing_child)
                remove_children.discard(existing_child)
                existing_child.copy_state(node)
            else:
                new_children.append(node)
    return (new_children, remove_children)
