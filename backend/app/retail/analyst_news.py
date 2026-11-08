"""Conservative literal analyst-action extraction from retained article headlines."""

import re
from collections.abc import Mapping
from decimal import Decimal

from app.market_data.strategy_inputs import AnalystDetails, HistoricalEvent, NewsDetails
from app.schemas.domain import canonical_hash

VERSION = "literal-news-analyst-v1"


def extract_action(
    article: HistoricalEvent, issuers: Mapping[str, tuple[str, ...]]
) -> tuple[HistoricalEvent | None, dict]:
    """Unmatched language remains a review finding, never a guessed financial fact."""
    proof = {
        "policy": VERSION,
        "article_id": article.event_id,
        "article_content_hash": article.original_content_hash,
        "source_url": article.source_url,
        "available_at": article.available_at.isoformat(),
        "headline": article.title,
    }
    if not isinstance(article.details, NewsDetails):
        raise ValueError("analyst extraction requires a retained news-version record")
    names = {name: symbol for symbol, aliases in issuers.items() for name in aliases}
    if len(names) != sum(len(aliases) for aliases in issuers.values()):
        raise ValueError("ambiguous issuer aliases")
    company = "(?:" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + ")"
    patterns = [
        rf"(?P<firm>.+?) (?P<verb>Maintains|Reiterates) (?P<grade>.+?) on (?P<issuer>{company})(?P<tail>, .+)?",
        rf"(?P<firm>.+?) (?P<verb>Upgrades|Downgrades) (?P<issuer>{company}) (?:from (?P<before>.+?) )?to (?P<grade>.+?)(?P<tail>, .+)?",
        rf"(?P<firm>.+?) (?P<verb>Initiates Coverage|Resumes Coverage) (?:on|On) (?P<issuer>{company}) (?:with|With) (?P<grade>.+?)(?: Rating)?(?P<tail>, .+)?",
    ]
    match = next((m for pattern in patterns if (m := re.fullmatch(pattern, article.title))), None)
    if not match:
        return None, {
            **proof,
            "status": "unresolved",
            "reason": "not an unambiguous supported single-issuer headline",
        }
    values = match.groupdict()
    symbol = names[values["issuer"]]
    grade = values["grade"].strip()
    firm = values["firm"].strip()
    # A finite vocabulary accepts facts actually printed; it does not translate
    # Buy into Outperform or infer the previous grade from an action verb.
    grades = {
        "Buy",
        "Sell",
        "Hold",
        "Neutral",
        "Outperform",
        "Underperform",
        "Overweight",
        "Underweight",
        "Equal-Weight",
        "Equal Weight",
        "Market Perform",
        "Sector Perform",
        "Sector Weight",
        "Strong Buy",
        "In-Line",
        "Peer Perform",
        "Positive",
        "Negative",
    }
    before = values.get("before")
    if (
        symbol not in article.symbols
        or grade not in grades
        or (before and before not in grades)
        or not 1 <= len(firm) <= 160
    ):
        return None, {
            **proof,
            "status": "unresolved",
            "reason": "issuer association, firm or printed grade needs review",
        }
    prior = current = None
    tags = []
    tail = values.get("tail")
    if tail:
        target = re.fullmatch(
            r", (?P<direction>Raises|Lowers|Maintains|Announces) (?:Price Target (?:to|at) \$(?P<value1>\d+(?:\.\d+)?)|\$(?P<value2>\d+(?:\.\d+)?) Price Target)(?: from \$(?P<prior>\d+(?:\.\d+)?))?",
            tail,
        )
        if not target:
            return None, {
                **proof,
                "status": "unresolved",
                "reason": "target clause is unsupported or ambiguous",
            }
        current = Decimal(target["value1"] or target["value2"])
        prior = Decimal(target["prior"]) if target["prior"] else None
        if not 0 < current <= 1_000_000 or (prior is not None and prior <= 0):
            return None, {**proof, "status": "unresolved", "reason": "invalid target amount"}
        direction = target["direction"]
        if prior is not None and (
            (direction == "Raises" and current <= prior)
            or (direction == "Lowers" and current >= prior)
            or (direction == "Maintains" and current != prior)
        ):
            return None, {
                **proof,
                "status": "unresolved",
                "reason": "target direction contradicts printed amounts",
            }
        tags.append("analyst.price_target")
        tags += {"Raises": ["analyst.target_raise"], "Lowers": ["analyst.target_lower"]}.get(
            direction, []
        )
    action = {
        "Maintains": "reiterate",
        "Reiterates": "reiterate",
        "Upgrades": "upgrade",
        "Downgrades": "downgrade",
        "Initiates Coverage": "initiate",
        "Resumes Coverage": "resume",
    }[values["verb"]]
    event = HistoricalEvent(
        event_id=f"news-analyst:{article.event_id}:{VERSION}",
        published_at=article.published_at,
        available_at=article.available_at,
        category="analyst." + action,
        tags=tags,
        symbols=[symbol],
        title=article.title,
        source_url=article.source_url,
        original_content_hash=article.original_content_hash,
        derivation="Literal single-issuer news headline, not original analyst report. Version-gated at source article availability. USD dollar-target interpretation requires reviewed US-issuer/feed scope; no adjusted target, consensus or missing prior inferred.",
        access=article.access,
        details=AnalystDetails(
            type="analyst",
            firm=firm,
            action=action,
            rating_before=before,
            rating_after=grade,
            target_before=prior,
            target_after=current,
            report_available_at=article.available_at,
        ),
    )
    return event, {
        **proof,
        "status": "extracted_unreviewed",
        "event_id": event.event_id,
        "symbol": symbol,
        "firm": firm,
        "action": action,
        "rating_before": before,
        "rating_after": grade,
        "target_before": str(prior) if prior is not None else None,
        "target_after": str(current) if current is not None else None,
        "currency_policy": "USD interpretation for the explicitly reviewed US-equity feed scope, not a currency conversion",
        "extraction_hash": canonical_hash(event.model_dump(mode="json")),
    }
