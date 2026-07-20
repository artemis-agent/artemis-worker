"""Tests for `fetch_crunchbase_website` \u2014 the Crunchbase URL/permalink
\u2192 official website resolver."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from artemis.discovery import sources as sources_mod
from artemis.discovery.sources import (
    crunchbase_logo_url,
    fetch_crunchbase_profile,
    fetch_crunchbase_website,
)


class _Resp:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _client_returning(resp: _Resp):
    """Build an AsyncMock that mimics `httpx.AsyncClient(...).__aenter__()`
    and returns a client whose `.post` resolves to `resp`."""
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx, client


@pytest.mark.asyncio
async def test_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "")
    assert await fetch_crunchbase_website("yubico") is None


@pytest.mark.asyncio
async def test_returns_none_for_empty_input(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    assert await fetch_crunchbase_website("") is None
    assert await fetch_crunchbase_website(None) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_extracts_permalink_from_full_url(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    captured: dict = {}

    resp = _Resp(200, {
        "entities": [
            {"properties": {"permalink": "yubico", "website_url": "http://www.yubico.com"}},
        ],
    })

    async def fake_post(url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json
        return resp

    client = AsyncMock()
    client.post = fake_post
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        out = await fetch_crunchbase_website(
            "https://www.crunchbase.com/organization/yubico"
        )

    assert out == "http://www.yubico.com"
    # The permalink (not the full URL) is what's sent to the API.
    assert captured["json"]["query"][0]["values"] == ["yubico"]


@pytest.mark.asyncio
async def test_picks_exact_permalink_match_among_fuzzy_results(monkeypatch):
    """`identifier contains` is fuzzy. We must filter for the exact
    permalink match in the response \u2014 a query for `stripe` would
    otherwise return `stripe-press`, `stripe-climate`, etc."""
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")

    resp = _Resp(200, {
        "entities": [
            {"properties": {"permalink": "stripe-press",
                            "website_url": "https://press.stripe.com"}},
            {"properties": {"permalink": "stripe",
                            "website_url": "https://stripe.com"}},
            {"properties": {"permalink": "stripe-climate",
                            "website_url": "https://climate.stripe.com"}},
        ],
    })
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        out = await fetch_crunchbase_website("stripe")
    assert out == "https://stripe.com"


@pytest.mark.asyncio
async def test_returns_none_when_no_exact_permalink_match(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    resp = _Resp(200, {
        "entities": [
            {"properties": {"permalink": "yubico-press",
                            "website_url": "https://press.yubico.com"}},
        ],
    })
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        assert await fetch_crunchbase_website("yubico") is None


@pytest.mark.asyncio
async def test_returns_none_on_non_200(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    ctx, _ = _client_returning(_Resp(429, text="rate limited"))
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        assert await fetch_crunchbase_website("yubico") is None


@pytest.mark.asyncio
async def test_returns_none_on_network_error(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")

    client = AsyncMock()
    client.post = AsyncMock(side_effect=RuntimeError("DNS failure"))
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        assert await fetch_crunchbase_website("yubico") is None


@pytest.mark.asyncio
async def test_rejects_input_with_slashes_outside_url_pattern(monkeypatch):
    """Defensive: if someone passes a weird path like `foo/bar`, don't
    forward it to the API — there's no valid permalink there."""
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    assert await fetch_crunchbase_website("foo/bar/baz") is None


# ── crunchbase_logo_url ───────────────────────────────────────────────────

def test_logo_url_construction():
    assert crunchbase_logo_url(
        "v1483638230/l94zqzbvxcixwf62yord.png"
    ) == "https://images.crunchbase.com/image/upload/v1483638230/l94zqzbvxcixwf62yord.png"


def test_logo_url_strips_leading_slash():
    """Be tolerant of accidental leading slashes in image_id."""
    assert crunchbase_logo_url(
        "/v1483638230/x.png"
    ) == "https://images.crunchbase.com/image/upload/v1483638230/x.png"


def test_logo_url_none_or_empty():
    assert crunchbase_logo_url(None) is None
    assert crunchbase_logo_url("") is None


# ── fetch_crunchbase_profile ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "")
    assert await fetch_crunchbase_profile("yubico") is None


@pytest.mark.asyncio
async def test_profile_flattens_payload(monkeypatch):
    """Verify the returned dict matches what the companies table expects:
    raw image_id preserved, logo URL constructed, social fields unwrapped
    from their {value: ...} envelopes."""
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")

    resp = _Resp(200, {
        "entities": [
            {
                "uuid": "dce5325d-f778-10ab-f2d1-ebd6dcdc00a3",
                "properties": {
                    "identifier": {
                        "permalink": "yubico",
                        "uuid": "dce5325d-f778-10ab-f2d1-ebd6dcdc00a3",
                        "value": "Yubico",
                        "image_id": "v1483638230/l94zqzbvxcixwf62yord.png",
                        "entity_def_id": "organization",
                    },
                    "website_url":       "http://www.yubico.com",
                    "short_description": "Yubico protects logins with hardware devices.",
                    "linkedin":          {"value": "https://www.linkedin.com/company/yubico/"},
                    "twitter":           {"value": "https://x.com/Yubico"},
                    "facebook":          {"value": "http://www.facebook.com/Yubikey"},
                },
            },
        ],
    })
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        profile = await fetch_crunchbase_profile("yubico")

    assert profile == {
        "crunchbase_permalink": "yubico",
        "crunchbase_uuid":      "dce5325d-f778-10ab-f2d1-ebd6dcdc00a3",
        "crunchbase_image_id":  "v1483638230/l94zqzbvxcixwf62yord.png",
        "name":                 "Yubico",
        "website":              "http://www.yubico.com",
        "logo_url":             "https://images.crunchbase.com/image/upload/v1483638230/l94zqzbvxcixwf62yord.png",
        "description":          "Yubico protects logins with hardware devices.",
        "linkedin_url":         "https://www.linkedin.com/company/yubico/",
        "twitter_url":          "https://x.com/Yubico",
        "facebook_url":         "http://www.facebook.com/Yubikey",
    }


@pytest.mark.asyncio
async def test_profile_picks_exact_permalink_match(monkeypatch):
    """The fuzzy `identifier contains` can return several orgs; we must
    pick the one whose permalink is exactly the slug we asked for."""
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")

    resp = _Resp(200, {
        "entities": [
            {"properties": {
                "identifier": {"permalink": "stripe-press", "value": "Stripe Press",
                               "image_id": "x/y.png"},
                "website_url": "https://press.stripe.com",
            }},
            {"properties": {
                "identifier": {"permalink": "stripe", "value": "Stripe",
                               "image_id": "real/stripe.png"},
                "website_url": "https://stripe.com",
            }},
        ],
    })
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        profile = await fetch_crunchbase_profile("stripe")

    assert profile is not None
    assert profile["crunchbase_permalink"] == "stripe"
    assert profile["website"] == "https://stripe.com"
    assert profile["logo_url"].endswith("real/stripe.png")


@pytest.mark.asyncio
async def test_profile_returns_none_on_no_match(monkeypatch):
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")
    resp = _Resp(200, {"entities": [
        {"properties": {"identifier": {"permalink": "yubico-press"}}},
    ]})
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        assert await fetch_crunchbase_profile("yubico") is None


@pytest.mark.asyncio
async def test_profile_handles_missing_social_fields(monkeypatch):
    """Crunchbase often omits social URLs. They should come back as None,
    not raise."""
    monkeypatch.setattr(sources_mod.settings, "crunchbase_api_key", "fake-key")

    resp = _Resp(200, {"entities": [{
        "properties": {
            "identifier": {"permalink": "tinyorg", "value": "TinyOrg",
                           "image_id": None},
            "website_url": None,
        },
    }]})
    ctx, _ = _client_returning(resp)
    with patch.object(sources_mod.httpx, "AsyncClient", return_value=ctx):
        profile = await fetch_crunchbase_profile("tinyorg")

    assert profile is not None
    assert profile["linkedin_url"] is None
    assert profile["twitter_url"] is None
    assert profile["facebook_url"] is None
    assert profile["logo_url"] is None
    assert profile["website"] is None
