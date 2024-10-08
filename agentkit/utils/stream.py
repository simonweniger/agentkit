from itertools import tee

from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


def get_first_element_and_iterator(iterator):
    # Create two copies of the iterator
    iter1, iter2 = tee(iterator, 2)

    first_element = next(iter1)
    return first_element, iter2


def merge_dicts(dict1, dict2):
    merged_dict = dict1.copy()
    for key, value in dict2.items():
        if key in merged_dict:
            merged_dict[key] = merge_values(merged_dict[key], value)
        else:
            merged_dict[key] = value
    return merged_dict


def merge_values(v1, v2):
    if v2 is None:
        return v1
    if isinstance(v2, ChatCompletionChunk):
        v2 = v2.model_dump()
    if isinstance(v2, dict):
        return merge_dicts(v1, v2)
    if isinstance(v2, str):
        return v1 + v2
    if isinstance(v2, int):
        return (v1 or []) + v2
    raise TypeError(f"Unsupported type {type(v2)}")
