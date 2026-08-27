#!/usr/bin/env python3
"""Check whether the Midea Portasplit is available on selected retailer pages."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


DEFAULT_PRODUCTS = [
    {
        "name": "Boulanger",
        "url": "https://www.boulanger.com/ref/1216685",
    },
    {
        "name": "Castorama",
        "url": "https://www.castorama.fr/climatiseur-portasplit-midea-reversible-3500w/8431312260509_CAFR.prd",
    },
    {
        "name": "Leroy Merlin",
        "url": "https://www.leroymerlin.fr/produits/climatiseur-split-mobile-reversible-portasplit-midea-par-optimea-93857579.html",
    },
]

COOKIE_BUTTON_TEXTS = [
    "Tout accepter",
    "Accepter tout",
    "J'accepte",
    "Accepter",
    "OK",
]

BLOCKED_PATTERNS = [
    r"\bcaptcha\b",
    r"\baccess denied\b",
    r"\bforbidden\b",
    r"acc[eè]s refus[eé]",
    r"v[ée]rifiez que vous [eê]tes humain",
    r"robot",
    r"unusual traffic",
]

UNAVAILABLE_PATTERNS = [
    r"indisponible",
    r"non disponible",
    r"momentan[ée]ment indisponible",
    r"rupture de stock",
    r"stock [ée]puis[ée]",
    r"produit [ée]puis[ée]",
    r"n.est plus disponible",
    r"pas vendu en ligne",
]

AVAILABLE_PATTERNS = [
    r"ajouter au panier",
    r"\ben stock\b",
    r"disponible en livraison",
    r"disponible en retrait",
    r"livraison [aà] domicile",
    r"retrait magasin",
]


@dataclass
class CheckResult:
    name: str
    url: str
    status: str
    evidence: list[str]
    final_url: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "evidence": self.evidence,
            "error": self.error,
        }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def matches(patterns: list[str], text: str) -> list[str]:
    found = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def classify(text: str) -> tuple[str, list[str]]:
    blocked = matches(BLOCKED_PATTERNS, text)
    if blocked:
        return "blocked", blocked[:5]

    unavailable = matches(UNAVAILABLE_PATTERNS, text)
    if unavailable:
        return "unavailable", unavailable[:5]

    available = matches(AVAILABLE_PATTERNS, text)
    if available:
        return "available", available[:5]

    return "unknown", []


async def dismiss_cookie_banner(page: Any) -> None:
    for label in COOKIE_BUTTON_TEXTS:
        try:
            button = page.get_by_role("button", name=re.compile(label, re.IGNORECASE)).first
            if await button.count():
                await button.click(timeout=2_000)
                return
        except Exception:
            pass


async def check_product(browser: Any, product: dict[str, str], timeout_ms: int) -> CheckResult:
    context = await browser.new_context(
        locale="fr-FR",
        timezone_id="Europe/Paris",
        viewport={"width": 1365, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
    )
    page = await context.new_page()

    try:
        response = await page.goto(product["url"], wait_until="domcontentloaded", timeout=timeout_ms)
        await dismiss_cookie_banner(page)
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except PlaywrightTimeoutError:
            pass

        text = normalize_text(await page.locator("body").inner_text(timeout=10_000))
        status, evidence = classify(text)
        http_status = response.status if response else None

        if http_status and http_status >= 400 and status == "unknown":
            status = "blocked" if http_status in {401, 403, 429} else "error"
            evidence = [f"http {http_status}"]

        return CheckResult(
            name=product["name"],
            url=product["url"],
            final_url=page.url,
            status=status,
            evidence=evidence,
        )
    except Exception as exc:
        return CheckResult(
            name=product["name"],
            url=product["url"],
            final_url=page.url if page else None,
            status="error",
            evidence=[],
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        await context.close()


async def run_checks(products: list[dict[str, str]], chromium_path: str, timeout_ms: int) -> dict[str, Any]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chromium_path,
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
            ],
        )
        try:
            results = await asyncio.gather(
                *(check_product(browser, product, timeout_ms) for product in products)
            )
        finally:
            await browser.close()

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": [result.as_dict() for result in results],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Midea Portasplit availability on configured retailer pages."
    )
    parser.add_argument(
        "--chromium",
        default="/usr/bin/chromium",
        help="Path to the Chromium executable.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30_000,
        help="Per-page navigation timeout in milliseconds.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="NAME=URL",
        help="Extra or replacement URL. Use NAME=URL. If set, only these URLs are checked.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print a compact human-readable summary instead of JSON.",
    )
    return parser.parse_args()


def products_from_args(url_args: list[str]) -> list[dict[str, str]]:
    if not url_args:
        return DEFAULT_PRODUCTS

    products = []
    for value in url_args:
        if "=" not in value:
            raise SystemExit(f"--url must use NAME=URL format, got: {value}")
        name, url = value.split("=", 1)
        products.append({"name": name.strip(), "url": url.strip()})
    return products


def print_pretty(payload: dict[str, Any]) -> None:
    print(f"Checked at: {payload['checked_at']}")
    for result in payload["results"]:
        evidence = ", ".join(result["evidence"]) if result["evidence"] else "no matched signal"
        print(f"- {result['name']}: {result['status']} ({evidence})")
        if result["error"]:
            print(f"  error: {result['error']}")
        print(f"  {result['url']}")


def main() -> int:
    args = parse_args()
    products = products_from_args(args.url)
    payload = asyncio.run(run_checks(products, args.chromium, args.timeout_ms))

    if args.pretty:
        print_pretty(payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    statuses = {result["status"] for result in payload["results"]}
    return 2 if statuses & {"error", "blocked"} else 0


if __name__ == "__main__":
    sys.exit(main())

