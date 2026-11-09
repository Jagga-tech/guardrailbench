"""Span-preserving evasion transforms and benign long-context padding."""
import base64
import codecs
import random

_LEET = str.maketrans("aeiost", "431057")
_HOMO = str.maketrans("aeopcxi", "аеорсхі")  # Cyrillic lookalikes

TRANSFORMS = {
    "base64": lambda s: base64.b64encode(s.encode()).decode(),
    "rot13": lambda s: codecs.encode(s, "rot13"),
    "leet": lambda s: s.translate(_LEET),
    "homoglyph": lambda s: s.translate(_HOMO),
    "zero_width": lambda s: "​".join(s),
    "unicode_tags": lambda s: "".join(
        chr(0xE0000 + ord(c)) if 0x20 <= ord(c) <= 0x7E else c for c in s
    ),
}


def apply_span(text: str, span: str, name: str) -> tuple[str, str]:
    if span not in text:
        raise ValueError("span not found in text")
    new_span = TRANSFORMS[name](span)
    return text.replace(span, new_span, 1), new_span


_FILLER = [
    "The Tuesday shipment left the Rotterdam warehouse two hours behind schedule.",
    "Meeting notes: the team agreed to review the vendor contracts next week.",
    "Quarterly revenue rose four percent compared with the same period last year.",
    "The regional office will move to the third floor in early March.",
    "Freight costs for the northern route fell slightly after the new carrier signed on.",
    "Attendance at the planning session was higher than expected.",
    "Inventory counts for the spring line were completed on Friday afternoon.",
    "The finance group closed the monthly books three days ahead of plan.",
    "A pallet of replacement parts arrived at the Denver depot this morning.",
    "Customer satisfaction scores held steady across all three service regions.",
    "The facilities team repainted the east lobby over the long weekend.",
    "Operating expenses came in under budget for the second quarter in a row.",
    "The warehouse in Lyon added a second evening shift to handle seasonal volume.",
    "Minutes from the last board meeting were circulated to all department heads.",
    "Packaging suppliers quoted a modest price increase starting in April.",
    "Headcount in the logistics division grew by six people this quarter.",
    "The annual supplier summit is scheduled for the middle of October.",
    "Delivery times to coastal customers improved by half a day on average.",
    "The training calendar for new hires was published on the shared drive.",
    "Gross margin on the premium product line reached its highest level in two years.",
    "The courier confirmed that the Thursday pickup will take place at noon.",
    "Budget requests for next year are due at the end of the month.",
    "A routine audit of the Osaka storage facility found no discrepancies.",
    "The marketing team presented its summer campaign calendar on Monday.",
    "Several trucks were rerouted after a bridge closure near the port.",
    "Sales in the western territory exceeded the forecast by roughly three percent.",
    "The cafeteria menu rotates every two weeks and is posted on the intranet.",
    "Maintenance on the loading dock doors is expected to wrap up by Wednesday.",
    "Return rates dropped after the packaging redesign went into production.",
    "The procurement office renewed its contract with the regional paper supplier.",
    "Cash flow remained positive throughout the quarter despite higher freight costs.",
    "Monthly shipping volume reached a new high of forty thousand parcels.",
    "The project timeline was adjusted to allow for an extra week of testing.",
    "Employee survey results will be shared at the all-hands meeting in June.",
    "The Chicago distribution center reported fewer late deliveries than last quarter.",
    "Travel expenses were reduced after the team consolidated its site visits.",
    "An updated organizational chart was posted on the company wiki.",
    "Receivables aged over sixty days declined for the third month running.",
    "The warehouse lighting upgrade is expected to lower energy costs by eight percent.",
    "Next quarter's staffing plan assumes steady demand through the holidays.",
]
assert len(_FILLER) == 40


def long_padding(text: str, span: str, seed: int, kb: int = 24) -> str:
    """Prepend ~kb KB of filler; filler is independent of span's content."""
    if span not in text:
        raise ValueError("span not found in text")
    rng = random.Random(seed)
    parts, size = [], 0
    while size < kb * 1000:
        s = rng.choice(_FILLER)
        parts.append(s)
        size += len(s) + 1
    return " ".join(parts) + "\n\n" + text
