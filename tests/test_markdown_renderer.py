import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MarkdownRendererContractTests(unittest.TestCase):
    def test_renderer_uses_dom_nodes_and_blocks_raw_html(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function inlineMarkdown", source)
        self.assertIn("function renderMarkdown", source)
        self.assertIn('node("table")', source)
        self.assertIn('const listType =', source)
        self.assertIn('const list = node(listType)', source)
        self.assertIn('"ul"', source)
        self.assertIn('"ol"', source)
        self.assertNotIn("innerHTML", source)

    def test_discovery_contract_has_exact_threshold(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function shouldResolve", source)
        self.assertIn("threshold = 110", source)
        self.assertIn("function resolveDiscoverCard", source)


if __name__ == "__main__":
    unittest.main()
