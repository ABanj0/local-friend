from unittest.mock import Mock

from local_agent.browser import Browser

from .support import WorkspaceTest


class BrowserPolicyTests(WorkspaceTest):
    def route(self, url, method="GET"):
        route = Mock()
        route.request.url = url
        route.request.method = method
        route.request.post_data = "sample"
        return route

    def test_outside_origin_is_blocked(self):
        route = self.route("https://evil.test")
        Browser(self.policy)._route(route)
        route.abort.assert_called_once()
        route.continue_.assert_not_called()

    def test_post_requires_confirmation(self):
        self.allow = False
        route = self.route("https://example.com/submit", "POST")
        Browser(self.policy)._route(route)
        route.abort.assert_called_once()
        self.assertEqual(self.approvals[0][0], "external_request")

    def test_allowed_read_does_not_need_confirmation(self):
        route = self.route("https://example.com")
        Browser(self.policy)._route(route)
        route.continue_.assert_called_once()
        self.assertFalse(self.approvals)
