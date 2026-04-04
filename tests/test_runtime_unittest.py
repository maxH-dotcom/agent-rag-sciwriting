import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agents.runtime import create_research_runtime, detect_langgraph_support, get_orchestration_runtime_info


class RuntimeDetectionTest(unittest.TestCase):
    def test_langgraph_detection_returns_structured_payload(self) -> None:
        result = detect_langgraph_support()
        self.assertIn("available", result)
        self.assertIn("reason", result)
        self.assertIn("version", result)

    def test_runtime_info_contains_effective_backend(self) -> None:
        result = get_orchestration_runtime_info()
        self.assertIn("configured_backend", result)
        self.assertIn("effective_backend", result)
        self.assertIn("checkpoint_status", result)
        self.assertIn("factory_ready", result)

    def test_runtime_factory_returns_runtime_object(self) -> None:
        runtime = create_research_runtime()
        self.assertTrue(hasattr(runtime, "run_until_pause"))
        self.assertTrue(hasattr(runtime, "runtime_name"))


if __name__ == "__main__":
    unittest.main()
