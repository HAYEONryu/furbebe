"""Source envelope validation. Preserve values and missing keys without coercion."""

from typing import Any

from pydantic import ConfigDict, RootModel


class SourceAnimalItem(RootModel[dict[str, Any]]):
    model_config = ConfigDict(strict=True)


class SourceShapeError(ValueError):
    """Messages contain schema paths only, never response values."""


def normalize_items(body: dict[str, Any]) -> tuple[list[SourceAnimalItem], str]:
    container = body.get("items")
    if container is None or container == "" or container == []:
        return [], "items_empty"
    if not isinstance(container, dict):
        raise SourceShapeError("body.items must be an object or empty")
    item = container.get("item")
    if item is None or item == "":
        return [], "item_empty"
    if isinstance(item, dict):
        values, shape = [item], "object"
    elif isinstance(item, list):
        values, shape = item, "array"
    else:
        raise SourceShapeError("body.items.item must be object, array or empty")
    if any(not isinstance(row, dict) for row in values):
        raise SourceShapeError("body.items.item contains a non-object row")
    return [SourceAnimalItem.model_validate(row) for row in values], shape


def source_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise SourceShapeError(field + " must be a nonnegative integer")
    if isinstance(value, str) and not value.isdecimal():
        raise SourceShapeError(field + " must be a nonnegative integer")
    result = int(value)
    if result < 0:
        raise SourceShapeError(field + " must be a nonnegative integer")
    return result
