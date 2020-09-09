from pathlib import Path
from typing import Union

from anytree import Node, RenderTree
from anytree.exporter import DotExporter

from gitta.template_tree import TemplateTree


def create_tree_node_representation(tree: TemplateTree):
    return Node(
        tree.get_template().to_flat_string(),
        children=[
            create_tree_node_representation(child) for child in tree.get_children()
        ],
    )


def render_tree_string(tree: TemplateTree):
    node = create_tree_node_representation(tree)
    result = ""
    for pre, fill, node in RenderTree(node):
        result += "%s%s\n" % (pre, node.name)

    return result


def render_tree_image(tree: TemplateTree, output_path: Union[str, Path]):
    if isinstance(output_path, Path):
        output_path = output_path.absolute()
    return DotExporter(create_tree_node_representation(tree)).to_picture(output_path)
