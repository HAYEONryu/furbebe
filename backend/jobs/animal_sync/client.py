"""Bounded HTTPS client. Never log an authenticated URL or source error body."""

import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote
from xml.etree import ElementTree

import httpx
from dotenv import dotenv_values

from .source_models import SourceShapeError, normalize_items, source_integer

ENDPOINT = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2"
REFERENCE_ENDPOINTS = {
    name: ENDPOINT.rsplit("/", 1)[0] + f"/{name}_v2"
    for name in ("sido", "sigungu", "kind", "shelter")
}
TRANSIENT_CODES = {"01", "05", "23"}
SUCCESS_CODES = {"00"}
SECRET_FIELD = re.compile(r"service.?key|password|token|private.?key|database_url", re.I)


class ApiFailure(RuntimeError):
    def __init__(self, kind: str, *, code: str | None = None, retryable: bool = False):
        self.kind = kind
        self.code = code if code and re.fullmatch(r"[A-Z0-9_]{1,64}", code) else None
        self.retryable = retryable
        super().__init__(kind + (f" (code={self.code})" if self.code else ""))


class Redactor:
    def __init__(self, key: str = ""):
        decoded = unquote(key)
        self.secrets = sorted(
            {s for s in (key, decoded, quote(decoded, safe="")) if s}, key=len, reverse=True
        )

    def text(self, value: Any, *, personal: bool = False) -> str:
        text = str(value)
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
        text = re.sub(
            r"(?i)(servicekey|data_go_kr_service_key|token|password)=([^&\s]+)",
            r"\1=[REDACTED]",
            text,
        )
        if personal:
            text = re.sub(r"https?://[^\s<>]+", "[URL]", text)
            text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
            text = re.sub(
                r"(?<!\d)(?:\+82[- ]?)?0\d{1,2}[- .]?\d{3,4}[- .]?\d{4}(?!\d)", "[PHONE]", text
            )
            text = re.sub(r"(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)", "[PERSONAL_ID]", text)
            text = re.sub(
                r"(?:성명|담당자|신고자|소유자|보호자|이름)\s*[:：]\s*\S+",
                "[PERSON_REDACTED]",
                text,
            )
        return text

    def tree(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                self.text(k): "[REDACTED]" if SECRET_FIELD.search(str(k)) else self.tree(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.tree(v) for v in value]
        return self.text(value) if isinstance(value, str) else value


def load_service_key(root: Path) -> str:
    value = os.environ.get("DATA_GO_KR_SERVICE_KEY")
    if not value:
        value = dotenv_values(root / ".env", interpolate=False, encoding="utf-8-sig").get(
            "DATA_GO_KR_SERVICE_KEY"
        )
    if not value or not value.strip():
        raise ApiFailure("MISSING_SERVICE_KEY: fill DATA_GO_KR_SERVICE_KEY in project .env")
    return unquote(value.strip())


@dataclass
class Page:
    number: int
    total: int
    items: list[dict[str, Any]]
    shape: str
    header: dict[str, Any]
    envelope: dict[str, Any]
    page_size: int | None


class AnimalApiClient:
    def __init__(
        self,
        key: str,
        *,
        transport=None,
        interval: float = 1.0,
        sleeper=time.sleep,
        max_retries: int = 3,
        timeout: float = 30,
    ):
        self.redactor = Redactor(key)
        self._key = key
        self.interval, self.sleep, self.max_retries = interval, sleeper, max_retries
        self.attempts = 0
        self.retries = 0
        self.errors: Counter = Counter()
        self.header_codes: Counter = Counter()
        self._last_request: float | None = None
        # HTTPX INFO messages contain query URLs. Suppress library network logs.
        for name in ("httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.CRITICAL)
        self.http = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10),
            transport=transport,
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()

    def _request(self, params: dict[str, Any], *, endpoint=ENDPOINT) -> httpx.Response:
        if self._last_request is not None:
            self.sleep(max(0, self.interval - (time.monotonic() - self._last_request)))
        self._last_request = time.monotonic()
        self.attempts += 1
        try:
            response = self.http.get(endpoint, params={**params, "serviceKey": self._key})
        except httpx.RequestError:
            raise ApiFailure("NETWORK_ERROR", retryable=True) from None
        if response.status_code != 200:
            raise ApiFailure(
                "HTTP_ERROR",
                code=str(response.status_code),
                retryable=response.status_code in {408, 429, 500, 502, 503, 504},
            )
        return response

    def fetch(self, page: int, size: int, *, filters: dict[str, str] | None = None) -> Page:
        return self._fetch(page, size, filters=filters)

    def fetch_reference(self, resource, page, size, *, filters=None):
        if resource not in REFERENCE_ENDPOINTS:
            raise ApiFailure("UNKNOWN_REFERENCE_RESOURCE")
        required = {
            "sido": set(),
            "sigungu": {"upr_cd"},
            "kind": {"up_kind_cd"},
            "shelter": {"upr_cd", "org_cd"},
        }[resource]
        filters = filters or {}
        if set(filters) != required or any(
            not isinstance(v, str) or not v.isascii() or not v.isdecimal() for v in filters.values()
        ):
            raise ApiFailure("INVALID_REFERENCE_FILTERS")
        return self._fetch(page, size, filters=filters, endpoint=REFERENCE_ENDPOINTS[resource])

    def _fetch(self, page, size, *, filters=None, endpoint=ENDPOINT):
        params = {"pageNo": page, "numOfRows": size, "_type": "json", **(filters or {})}
        for attempt in range(self.max_retries + 1):
            try:
                response = self._request(params, endpoint=endpoint)
                try:
                    payload = response.json()
                except ValueError:
                    # data.go.kr gateway errors may be XML even when JSON was requested.
                    try:
                        xml = ElementTree.fromstring(response.content)
                        code = xml.findtext(".//returnReasonCode") or xml.findtext(".//resultCode")
                    except ElementTree.ParseError:
                        code = None
                    if code:
                        raise ApiFailure(
                            "APPLICATION_ERROR", code=code, retryable=code in TRANSIENT_CODES
                        ) from None
                    raise ApiFailure("NON_JSON_RESPONSE") from None
                return self._parse(payload, page, allow_unwrapped=endpoint != ENDPOINT)
            except ApiFailure as exc:
                self.errors[str(exc)] += 1
                if not exc.retryable or attempt == self.max_retries:
                    raise
                self.retries += 1
                self.sleep(2**attempt)
        raise AssertionError("unreachable")

    def _parse(self, payload: Any, requested_page: int, *, allow_unwrapped=False) -> Page:
        if allow_unwrapped and isinstance(payload, dict) and "response" not in payload:
            payload = {"response": payload}
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), dict):
            raise ApiFailure("RESPONSE_SHAPE_UNRESOLVED")
        response = payload["response"]
        header = response.get("header")
        if not isinstance(header, dict):
            raise ApiFailure("HEADER_SHAPE_UNRESOLVED")
        code = str(header.get("resultCode", ""))
        safe_code = code if re.fullmatch(r"[A-Z0-9_]{1,64}", code) else "UNRECOGNIZED"
        self.header_codes[safe_code] += 1
        if code not in SUCCESS_CODES:
            raise ApiFailure("APPLICATION_ERROR", code=code, retryable=code in TRANSIENT_CODES)
        body = response.get("body")
        if not isinstance(body, dict):
            raise ApiFailure("BODY_SHAPE_UNRESOLVED")
        try:
            total = source_integer(body.get("totalCount"), "totalCount")
            if "pageNo" in body and source_integer(body["pageNo"], "pageNo") != requested_page:
                raise SourceShapeError("response pageNo differs from requested page")
            page_size = (
                source_integer(body["numOfRows"], "numOfRows") if "numOfRows" in body else None
            )
            items, shape = normalize_items(body)
        except (SourceShapeError, ValueError):
            raise ApiFailure("RESPONSE_SHAPE_UNRESOLVED") from None
        clean = self.redactor.tree(payload)
        return Page(
            requested_page,
            total,
            [self.redactor.tree(row.root) for row in items],
            shape,
            self.redactor.tree(header),
            clean,
            page_size,
        )
