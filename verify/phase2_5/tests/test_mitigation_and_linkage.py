from __future__ import annotations

import unittest

from src.phase2_5_reliability.mitigation_register_builder import MitigationRegisterBuilder
from src.phase2_5_reliability.phase_linkage_builder import PhaseLinkageBuilder


class MitigationAndLinkageTests(unittest.TestCase):
    def test_every_mitigation_decision_is_pending(self) -> None:
        linkage = PhaseLinkageBuilder().build()
        register = MitigationRegisterBuilder().build(linkage)
        self.assertEqual(len(register), 8)
        self.assertTrue(register["mitigation_status"].eq("pending").all())
        self.assertTrue(register["mitigation_decision"].str.startswith("Pending").all())


if __name__ == "__main__":
    unittest.main()
