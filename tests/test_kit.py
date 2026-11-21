"""Tests: the browser scripts (dist/*.js) in a real browser against a local test site (no access to any real site), the hard
stops, and kit.py on the downloaded files. Browser: chromium (Edge on Windows) or CISCE_TEST_BROWSER=firefox."""
import csv
import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
import kit  # noqa: E402

PAGES = Path(__file__).parent / "pages"
RESULT = (PAGES / "result-isc-india-p1.html").read_bytes().replace(b"of 1928 entries", b"of 30 entries")   # 3 pages
CHALLENGE = (PAGES / "cloudflare-challenge.html").read_bytes()
PDF = b"%PDF-1.4\n% test file\n%%EOF\n"


class Site(http.server.BaseHTTPRequestHandler):
    """/?page=N: a locator page (3 pages in all). /doc/*: files for list mode. `page2` sets the first answers for page 2."""
    page2 = []            # e.g. ["challenge"], ["429"] * 4, ["403"]: one answer per request for page 2, then normal pages
    log = []

    def do_GET(self):
        Site.log.append(self.path)
        status, body, ctype, extra = 200, RESULT, "text/html; charset=utf-8", {}
        if self.path.endswith("page=2") and Site.page2:
            kind = Site.page2.pop(0)
            status, body = {"challenge": (403, CHALLENGE), "429": (429, b"slow down"), "403": (403, b"Forbidden"),
                            "500": (500, b"<html><script src='/cdn-cgi/challenge-platform/x.js'></script></html>")}[kind]
            if kind == "429":
                extra["Retry-After"] = "0"
        elif self.path.startswith("/doc/"):
            status, body = {"/doc/a.html": (200, b"<html>A</html>"), "/doc/b.pdf": (200, PDF)}.get(self.path, (404, b"not found"))
            ctype = "application/pdf" if self.path.endswith(".pdf") else ctype
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def run(tmp_path, target, until, test=None, page2=(), urls=None, stop_after=None):
    """Run dist/<target>.js; returns (dialog messages, Downloads folder). Clicks Continue in the box when it shows."""
    from playwright.sync_api import sync_playwright
    Site.page2, Site.log = list(page2), []
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    downloads, dialogs = tmp_path / "Downloads", []
    downloads.mkdir(exist_ok=True)
    with sync_playwright() as p:
        kind = os.environ.get("CISCE_TEST_BROWSER", "chromium")
        browser = p.firefox.launch() if kind == "firefox" else p.chromium.launch(channel="msedge" if sys.platform == "win32" else None)
        page = browser.new_page(accept_downloads=True)
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept("1") if d.type == "prompt" else d.accept()))
        page.on("download", lambda d: d.save_as(downloads / d.suggested_filename))
        page.goto(f"http://127.0.0.1:{srv.server_port}/?page=1")
        page.evaluate(f"localStorage.clear(); window.KIT_TEST = {json.dumps({'delayMs': 0, 'retryMs': 200, **(test or {})})}")
        page.add_script_tag(content=(ROOT / "dist" / f"{target}.js").read_text(encoding="utf-8"))
        if urls:
            page.locator("textarea").fill("\n".join(urls))
            page.get_by_role("button", name="Start").click()
        end = time.time() + 40
        while not any(until in m for m in dialogs) and time.time() < end:
            go = page.get_by_role("button", name="Continue")
            if go.count() and go.is_visible():
                dialogs.append("box: " + page.evaluate("document.querySelector('div[style*=\"2147483647\"] span').textContent"))
                go.click()
            if stop_after and page.evaluate("window.kitRun && window.kitRun.next") == stop_after + 1:
                page.get_by_role("button", name="Stop").click()
                stop_after = None
            page.wait_for_timeout(100)
        page.wait_for_timeout(700)
        run.resume = page.evaluate("localStorage.getItem('kit-%s-resume')" % target.replace("-list", "").replace("cisce-org", "cisce-org"))
        assert page.locator("textarea").count() == 0          # the box is gone at the end
        browser.close()
    srv.shutdown()
    return dialogs, downloads


def names(folder):
    return sorted(f.name for f in folder.iterdir())


def test_dist_is_built_from_sources():
    files = build.build()
    assert all(p.read_text(encoding="utf-8") == text for p, text in files.items())


def test_parse_result_page():
    rows = dict(kit.parse((PAGES / "result-isc-india-p1.html").read_text(encoding="utf-8")))
    assert len(rows) == 10 and rows["AN001"]["pin"] == "744103"


def test_locator_with_a_check_then_csv(tmp_path):
    dialogs, dl = run(tmp_path, "cisce-locator", "done", page2=["challenge"])
    assert any("Verify you are human" in m for m in dialogs)
    assert names(dl) == ["cisce-pages-0001-0001.json", "cisce-pages-0002-0003.json"]
    out = tmp_path / "out"
    done = kit.unpack(out, [dl])
    assert done == {"cisce-locator": 3}
    assert kit.write_csv(out / "cisce-locator") == 10


def test_server_error_is_retried_not_a_check(tmp_path):
    dialogs, dl = run(tmp_path, "cisce-locator", "done", page2=["500"])
    assert not any("Verify" in m for m in dialogs) and names(dl) == ["cisce-pages-0001-0003.json"]


def test_hard_stop_after_repeated_429(tmp_path):
    dialogs, dl = run(tmp_path, "cisce-locator", "hard stop", page2=["429"] * 4)
    assert any("answered 429 4 times" in m for m in dialogs) and names(dl) == ["cisce-pages-0001-0001.json"]


def test_hard_stop_on_403_block(tmp_path):
    dialogs, _ = run(tmp_path, "cisce-locator", "hard stop", page2=["403"])
    assert any("refused (HTTP 403)" in m for m in dialogs)


def test_hard_stop_page_cap_and_day_cap(tmp_path):
    dialogs, dl = run(tmp_path, "cisce-locator", "hard stop", test={"maxPages": 2})
    assert any("2 pages in this run" in m for m in dialogs) and names(dl) == ["cisce-pages-0001-0002.json"]
    (tmp_path / "b").mkdir()
    dialogs, _ = run(tmp_path / "b", "cisce-locator", "hard stop", test={"dayCap": 1})
    assert any("daily limit" in m for m in dialogs)


def test_stop_button_and_resume(tmp_path):
    dialogs, dl = run(tmp_path, "cisce-locator", "stopped", test={"delayMs": 5000}, stop_after=1)
    assert any("stopped before page 2" in m for m in dialogs) and names(dl) == ["cisce-pages-0001-0001.json"]
    assert json.loads(run.resume)["next"] == 2


def test_list_mode_html_pdf_and_404(tmp_path):
    urls = ["/doc/a.html", "/doc/b.pdf", "/doc/missing.html", "https://example.org/other-site.html"]
    dialogs, dl = run(tmp_path, "url-list", "done", urls=urls)
    assert names(dl) == ["url-list-0001-0003.json", "url-list-0002-b.pdf"]
    data = json.loads((dl / "url-list-0001-0003.json").read_text())
    assert data["url-0001.html"] == "<html>A</html>" and data["_meta"]["urls"]["url-0003.html"]["status"] == 404
    out = tmp_path / "out"
    kit.unpack(out, [dl])
    assert (out / "url-list" / "files" / "url-list-0002-b.pdf").read_bytes() == PDF
    rows = list(csv.DictReader(open(out / "url-list" / "urls.csv", encoding="utf-8-sig")))
    assert [r["status"] for r in rows] == ["200", "200", "404"]


def test_old_saver_files_and_broken_files(tmp_path, capsys):
    dl = tmp_path / "Downloads"
    dl.mkdir()
    (dl / "cisce-pages-0001-0001.json").write_text(json.dumps({"page-0001.html": RESULT.decode()}), encoding="utf-8")
    (dl / "cisce-pages-0002-0002.json").write_text("{broken", encoding="utf-8")
    (dl / "cisce-pages-0003-0003.json").write_text(json.dumps({"../evil.html": "x", "page-0003.html": RESULT.decode()}), encoding="utf-8")
    out = tmp_path / "out"
    assert kit.unpack(out, [dl]) == {"cisce-locator": 2}
    assert names(out / "cisce-locator" / "pages") == ["page-0001.html", "page-0003.html"]
    kit.write_csv(out / "cisce-locator")
    text = capsys.readouterr().out
    assert "cannot read" in text and "Missing pages (1): 2" in text


@pytest.mark.parametrize("target", ["cisce-locator", "cisce-org-list", "url-list"])
def test_min_delay_is_five_seconds_on_real_sites(target):
    src = (ROOT / "dist" / f"{target}.js").read_text(encoding="utf-8")
    assert "Math.max(T.minDelayMs ?? 6000, 5000)" in src and "local ? (window.KIT_TEST" in src
