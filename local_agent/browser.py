"""Isolated Playwright context with origin and network-method enforcement."""
from .captures import Captures
from .file_ops import parent_identity, publish, staging
from .review import require_unchanged
from .safety import Denied


class Browser:
    def __init__(self, policy, capture=None):
        self.policy = policy
        self.driver = self.browser = self.context = None
        self.pages = {}
        self.capture = capture
        self.captures = None

    def start(self):
        if self.context:
            return
        from playwright.sync_api import sync_playwright
        self.driver = sync_playwright().start()
        options = {"headless": self.policy.config["browser"]["headless"]}
        channel = self.policy.config["browser"].get("channel")
        if channel:
            options["channel"] = channel
        self.browser = self.driver.chromium.launch(**options)
        self.context = self.browser.new_context(accept_downloads=True, service_workers="block")
        self.context.set_default_timeout(self.policy.config["browser"]["timeout_ms"])
        self.context.route("**/*", self._route)
        # WebSocket traffic bypasses HTTP routes unless explicitly blocked.
        self.context.route_web_socket("**/*", lambda socket: socket.close())

    def _route(self, route):
        request = route.request
        try:
            self.policy.check_stop()
            self.policy.origin(request.url)
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                self.policy.confirm("external_request", {"url": request.url,
                                    "method": request.method, "body": request.post_data})
            route.continue_()
        except Denied:
            route.abort()

    def page(self, tab):
        self.policy.check_stop()
        if tab not in self.pages or self.pages[tab].is_closed():
            raise ValueError("Unknown or closed tab; use browser_open")
        return self.pages[tab]

    def open(self, url, tab="main"):
        self.policy.origin(url)
        self.start()
        page = self.pages.get(tab)
        if page is None or page.is_closed():
            page = self.context.new_page()
            self.pages[tab] = page
        # One retry only for read-only navigation; never replay mutations.
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        for attempt in range(2):
            self.policy.check_stop()
            try:
                page.goto(url, wait_until="domcontentloaded")
                return self.read(tab)
            except PlaywrightTimeout:
                if attempt:
                    raise

    def read(self, tab="main"):
        page = self.page(tab)
        self.policy.origin(page.url)
        links = page.locator("a[href]").evaluate_all(
            "elements => elements.slice(0,50).map(e => ({text:e.innerText,url:e.href}))")
        return {"tab": tab, "url": page.url, "title": page.title(),
                "text": page.locator("body").inner_text()[:12000], "links": links}

    def click(self, selector, tab="main"):
        page = self.page(tab)
        self.policy.confirm("browser_click", {"url": page.url, "selector": selector,
                            "warning": "Clicks may submit, purchase, send or change settings."})
        page.locator(selector).click()
        return {"tab": tab, "url": page.url, "clicked": selector}

    def fill(self, selector, text, tab="main"):
        page = self.page(tab)
        self.policy.confirm("browser_fill", {"url": page.url, "selector": selector, "text": text,
                            "warning": "Some pages send input before form submission."})
        page.locator(selector).fill(text)
        return {"tab": tab, "filled": selector}

    def download(self, selector, path, tab="main"):
        destination = self.policy.path(path, write=True)
        if destination.exists():
            raise Denied("Download destination must be new")
        page = self.page(tab)
        self.policy.confirm("browser_download", {"url": page.url, "selector": selector, "path": path})
        require_unchanged(str(destination), str(self.policy.path(path, write=True)))
        if destination.exists():
            raise Denied("Review conflict: download destination appeared; request a fresh review")
        destination.parent.mkdir(parents=True, exist_ok=True)
        parent = parent_identity(destination.parent)
        with staging(destination) as staged:
            with page.expect_download() as info:
                page.locator(selector).click()
            info.value.save_as(str(staged))
            publish(self.policy, path, staged, destination, None, parent)
        return {"path": path, "bytes": destination.stat().st_size, "trusted": False}

    def screenshot(self, tab="main"):
        data = self.page(tab).screenshot()
        if self.capture:
            return {"image_path": self.capture(data)}
        if self.captures is None:
            self.captures = Captures(self.policy.state)
        return {"image_path": self.captures.write(data)}

    def intervene(self, tab="main"):
        page = self.page(tab)
        if self.policy.config["browser"]["headless"]:
            raise ValueError("Use Browser mode with a visible browser for authentication")
        page.bring_to_front()
        self.policy.confirm("browser_intervention", {
            "tab": tab, "url": page.url,
            "instruction": "Complete authentication in the browser, then approve Continue. "
                           "Do not type credentials into the assistant. Submission approvals still apply."})
        return self.read(tab)

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.driver:
                self.driver.stop()
        finally:
            if self.captures:
                self.captures.close()
