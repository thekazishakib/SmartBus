"""Create original SVG documentation illustrations with no extra dependencies."""

import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from project_profile import load_profile  # noqa: E402 -- root added above


def text(x, y, value, size=20, color="#233d39", bold=False):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{escape(value)}</text>'


def frame(title, subtitle):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="650" viewBox="0 0 1200 650" role="img">',
        f"<title>{escape(title)}</title>",
        '<rect width="1200" height="650" rx="20" fill="#f4f7f6"/>',
        text(42, 48, "SMARTBUS", 15, "#22675f", True),
        text(42, 95, title, 32, bold=True),
        text(42, 127, subtitle, 17, "#60726d"),
        text(950, 48, "Workflow illustration", 14, "#60726d"),
    ]


def cards(parts, items, width=210, gap=18):
    for index, (title, lines) in enumerate(items):
        x = 42 + index * (width + gap)
        parts.append(
            f'<rect x="{x}" y="170" width="{width}" height="250" rx="12" fill="white" stroke="#d5e1dc"/>'
        )
        parts.append(f'<circle cx="{x + 30}" cy="205" r="16" fill="#e4f0eb"/>')
        parts.append(text(x + 25, 211, str(index + 1), 17, "#22675f", True))
        for offset, line in enumerate(title):
            parts.append(text(x + 20, 251 + offset * 28, line, 21, bold=True))
        for offset, line in enumerate(lines):
            parts.append(text(x + 20, 322 + offset * 25, line, 16, "#60726d"))


def main():
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    parts = frame(
        "From daily entries to accepted accounts",
        "A simple sequence with a visible review before final reporting.",
    )
    cards(
        parts,
        [
            (["Save Excel"], ["Trips and collections", "Save and close the file."]),
            (["Import"], ["Capture accepted values.", "Keep a source backup."]),
            (["Review"], ["Resolve invalid entries.", "Enter known receipts."]),
            (["Close day"], ["Publish this revision.", "Keep historical values."]),
            (["Export"], ["Choose the date range.", "Excel or printable report."]),
        ],
    )
    parts += [
        '<rect x="42" y="460" width="1116" height="142" rx="12" fill="#e6efeb"/>',
        text(66, 494, "Need a correction?", 22, bold=True),
        text(
            66,
            527,
            "Record a reason, edit and save the source, then import, review and close the replacement.",
            19,
        ),
        text(
            66,
            560,
            "The previous closed revision remains in final reports until the replacement closes.",
            18,
            "#60726d",
        ),
        "</svg>",
    ]
    (assets / "07-review-workflow.svg").write_text("".join(parts), encoding="utf-8")
    parts = frame(
        "Export your report as PDF",
        "Use the normal browser print dialog. No new Python package is needed.",
    )
    cards(
        parts,
        [
            (
                ["Choose report"],
                ["Company and date range", "Use closed daily records."],
            ),
            (
                ["Open printable", "report"],
                ["Click the generated link.", "Review the report totals."],
            ),
            (
                ["Print / Save", "as PDF"],
                ["Click the report button", "or press Ctrl+P."],
            ),
            (["Save the PDF"], ["Select Save as PDF.", "Choose a folder and save."]),
        ],
        width=264,
        gap=20,
    )
    parts += [
        '<rect x="42" y="460" width="1116" height="142" rx="12" fill="#e6efeb"/>',
        text(66, 495, "Recommended print settings", 22, bold=True),
        text(
            66, 531, "Legal paper  |  Portrait  |  Browser headers and footers off", 20
        ),
        text(
            66,
            565,
            "Enable background graphics if available. The report toolbar is hidden in the printed output.",
            18,
            "#60726d",
        ),
        "</svg>",
    ]
    (assets / "08-pdf-export.svg").write_text("".join(parts), encoding="utf-8")
    profile = load_profile(ROOT)
    logo = f'''<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96" role="img"><title>{escape(profile["project_name"])} logo</title><rect width="96" height="96" rx="22" fill="{profile["accent_color"]}"/><rect x="22" y="23" width="52" height="45" rx="10" fill="none" stroke="white" stroke-width="4"/><path d="M23 45h50M48 25v20" stroke="white" stroke-width="3"/><circle cx="32" cy="73" r="6" fill="white"/><circle cx="64" cy="73" r="6" fill="white"/><circle cx="33" cy="57" r="3" fill="white"/><circle cx="63" cy="57" r="3" fill="white"/></svg>'''
    (assets / "logo.svg").write_text(logo, encoding="utf-8")
    print("Created logo and two original workflow illustrations.")


if __name__ == "__main__":
    main()
