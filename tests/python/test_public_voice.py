"""The site speaks as "we". Public pages must not describe our work as done by a
"bot", or label sections "hand-edited" / "auto-written". HTML comments, scripts
and styles are ignored (editor notes there may name the news bot).

Run: python -m unittest discover -s tests/python
"""
import html
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {"logo-concepts.html", "logo-concepts-v2.html", "test-takeaction.html"}
BANNED = re.compile(r"\b(bots?|hand-?edited|hand-?curated|auto-?written|auto-?generated)\b", re.I)


def public_pages() -> list[Path]:
    root = [p for p in ROOT.glob("*.html") if p.name not in EXCLUDED]
    return sorted(root + list((ROOT / "parks").glob("*.html")))


def visible_text(page: str) -> str:
    page = re.sub(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>", " ", page, flags=re.S | re.I)
    attrs = " ".join(re.findall(r'\b(?:title|aria-label|alt|placeholder)="([^"]*)"', page))
    return html.unescape(re.sub(r"<[^>]+>", " ", page) + " " + attrs)


class PublicVoiceTest(unittest.TestCase):
    def test_no_bot_or_hand_edited_wording(self):
        found = []
        for p in public_pages():
            for m in BANNED.finditer(visible_text(p.read_text(encoding="utf-8"))):
                found.append(f"{p.relative_to(ROOT)}: {m.group(0)!r}")
        self.assertEqual(found, [])

    def test_detector_sees_visible_text_but_not_comments(self):
        self.assertTrue(BANNED.search(visible_text("<p>Every day a bot reads the news</p>")))
        self.assertTrue(BANNED.search(visible_text('<span class="tag">Hand-edited</span>')))
        self.assertFalse(BANNED.search(visible_text("<!-- the news bot writes this --><p>We update it</p>")))
        self.assertFalse(BANNED.search(visible_text("<p>the bottom of the robot both</p>")))


if __name__ == "__main__":
    unittest.main()
