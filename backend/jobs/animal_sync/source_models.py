"""Source envelope validation. Preserve values and missing keys without coercion."""

from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel, field_validator

from .parsing import meaningful


class ValidatedAnimal(BaseModel):
    """Strict production boundary; unknown fields and missing keys remain in the raw snapshot."""

    model_config = ConfigDict(strict=True, extra="allow", hide_input_in_errors=True)

    desertionNo: str
    noticeNo: str | None = None
    rfidCd: str | None = None
    upKindCd: str | None = None
    upKindNm: str | None = None
    kindCd: str | None = None
    kindNm: str | None = None
    kindFullNm: str | None = None
    sexCd: str | None = None
    neuterYn: str | None = None
    age: str | None = None
    weight: str | None = None
    colorCd: str | None = None
    happenDt: str | None = None
    happenPlace: str | None = None
    processState: str | None = None
    endReason: str | None = None
    noticeSdt: str | None = None
    noticeEdt: str | None = None
    specialMark: str | None = None
    sfeSoci: str | None = None
    sfeHealth: str | None = None
    etcBigo: str | None = None
    vaccinationChk: str | None = None
    healthChk: str | None = None
    careRegNo: str | None = None
    careNm: str | None = None
    careTel: str | None = None
    careAddr: str | None = None
    careOwnerNm: str | None = None
    orgNm: str | None = None
    updTm: str | None = None
    popfile1: str | None = None
    popfile2: str | None = None
    popfile3: str | None = None
    popfile4: str | None = None
    popfile5: str | None = None
    popfile6: str | None = None
    popfile7: str | None = None
    popfile8: str | None = None

    @field_validator("desertionNo")
    @classmethod
    def usable_identity(cls, value):
        if not meaningful(value):
            raise ValueError("Source identity is required")
        return value


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
