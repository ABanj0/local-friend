"""Keep suite accounting honest without running live or fixture workflows twice."""
import os
import unittest
from collections import Counter
from pathlib import Path

from . import studio_socket_support, studio_support, studio_ui_support


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


class DiscoveryTests(unittest.TestCase):
    def test_discovery_has_no_duplicate_ids_or_inherited_implementations(self):
        root = Path(__file__).resolve().parents[1]
        discovered = list(cases(unittest.TestLoader().discover(
            str(root / "tests"), top_level_dir=str(root))))
        identities = Counter(case.id() for case in discovered)
        implementations = Counter(
            (method.__module__, method.__qualname__)
            for case in discovered
            for method in [getattr(type(case), case._testMethodName)]
        )
        self.assertFalse({key: count for key, count in identities.items() if count > 1})
        self.assertFalse({key: count for key, count in implementations.items() if count > 1})

    def test_shared_fixtures_are_not_discoverable_test_cases(self):
        for fixture in (studio_support.StudioAPIFixture, studio_support.StudioProcessFixture,
                        studio_ui_support.StudioUIFixture, studio_socket_support.StudioSocketFixture):
            with self.subTest(fixture=fixture.__name__):
                self.assertFalse(issubclass(fixture, unittest.TestCase))
        for module in (studio_support, studio_ui_support, studio_socket_support):
            with self.subTest(module=module.__name__):
                self.assertEqual(unittest.TestLoader().loadTestsFromModule(module).countTestCases(), 0)

    def test_both_ui_scenarios_remain_distinct_and_opt_in(self):
        from . import test_slash_ui, test_studio_ui

        loader = unittest.TestLoader()
        chat = list(cases(loader.loadTestsFromModule(test_studio_ui)))
        slash = list(cases(loader.loadTestsFromModule(test_slash_ui)))
        self.assertEqual([case.id() for case in chat], [
            "tests.test_studio_ui.StudioUITests.test_chat_attachment_management"])
        self.assertEqual([case.id() for case in slash], [
            "tests.test_slash_ui.SlashUITests.test_slash_commands_and_chat_attachment_management"])
        for case in [*chat, *slash]:
            with self.subTest(case=case.id()):
                self.assertEqual(bool(getattr(type(case), "__unittest_skip__", False)),
                                 os.getenv("LIVE_STUDIO_UI") != "1")
