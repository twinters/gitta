import json
from typing import Callable, List

from nltk.tokenize.treebank import TreebankWordDetokenizer

from context_free_grammar import ContextFreeGrammar
from template import Template
from template_elements import TemplateSlot


def triangle_slot_mapper(slot: TemplateSlot):
    return "<" + slot.get_name() + ">"


def hashtag_slot_mapper(slot: TemplateSlot):
    return "#" + slot.get_name() + "#"


def convert_template(
    template: Template,
    slot_mapper=triangle_slot_mapper,
    detokenizer: Callable[[List[str]], str] = TreebankWordDetokenizer().detokenize,
):
    elements = [str(el) for el in template.get_elements()]
    return detokenizer(elements)


def _to_json(grammar: ContextFreeGrammar, slot_mapper=triangle_slot_mapper):
    converted = dict()
    for slot in grammar.get_slots_sorted():
        values = list(
            convert_template(val, hashtag_slot_mapper)
            for val in grammar.get_content_for(slot)
        )
        values.sort()
        converted[slot.get_name()] = values

    return converted


def to_tracery(grammar: ContextFreeGrammar):
    converted = _to_json(grammar, slot_mapper=hashtag_slot_mapper)
    result = json.dumps(converted, indent=4)
    return result


def to_arrow_notation(grammar: ContextFreeGrammar):
    converted = _to_json(grammar, slot_mapper=triangle_slot_mapper)
    lines = []
    for slot in converted:
        lines.append(slot.get_name() + " -> " + " | ".join(converted[slot]))

    return "\n".join(lines)
