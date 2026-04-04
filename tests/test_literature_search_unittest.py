import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agents.tools.literature_search import retrieve_literature


class LiteratureSearchTest(unittest.TestCase):
    def test_fallback_search_returns_chunks_and_stats(self) -> None:
        result = retrieve_literature("我想分析农业产值对碳排放的影响")
        self.assertGreater(len(result["all_chunks"]), 0)
        self.assertIn("source_stats", result)
        self.assertGreaterEqual(result["source_stats"]["fallback"], 1)
        self.assertGreater(result["quality_score"], 0.5)

    def test_local_paper_files_are_reflected(self) -> None:
        result = retrieve_literature(
            "测试本地论文输入",
            paper_files=["/tmp/paper_a.pdf", "/tmp/paper_b.pdf"],
        )
        self.assertEqual(result["source_stats"]["local_file"], 2)
        local_refs = [ref for ref in result["references"] if ref["source_type"] == "local_file"]
        self.assertEqual(len(local_refs), 2)


if __name__ == "__main__":
    unittest.main()
