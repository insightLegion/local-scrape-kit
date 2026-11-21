// ---- local-scrape-kit engine (do not edit dist/*.js by hand: edit engine.js or targets/*.js, then run python build.py) ----
// Runs in the page of the target site, in your normal browser, after YOU passed any check ("Verify you are human").
// It never clicks or solves a check. It reads one URL at a time with your own session and downloads the pages in files.
(async () => {
  const KIT_VERSION = "1.0";
  const T = TARGET;
  const local = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const test = local ? (window.KIT_TEST || {}) : {};          // test overrides work only on a local test server
  if (!local && T.hosts && !T.hosts.includes(location.hostname)) { alert(`Open https://${T.hosts[0]}/ first, then paste this script in that tab.`); return; }
  if (window.kitRun) { alert("A run is already active in this tab. Click Stop in its box first."); return; }

  // Rate limits and hard stops. The minimum delay cannot go below 5 s on a real site.
  const BASE_DELAY = test.delayMs ?? Math.max(T.minDelayMs ?? 6000, 5000), JITTER = test.delayMs != null ? 0 : 2000;
  const RETRY_MS = test.retryMs ?? 120000, MAX_429 = 3, MAX_ERRORS = 5, SLOW_MS = 10000, MAX_DELAY = 60000;
  const MAX_PAGES = test.maxPages ?? T.maxPages ?? 400, MAX_MINUTES = T.maxMinutes ?? 120, DAY_CAP = test.dayCap ?? T.dayCap ?? 1000;
  const CHUNK = test.chunk ?? T.chunk ?? 50, KEY = `kit-${T.name}`;

  const store = {   // small state in this site's localStorage; a private window can refuse it, then the run works without it
    get: k => { try { return JSON.parse(localStorage.getItem(`${KEY}-${k}`)); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(`${KEY}-${k}`) : localStorage.setItem(`${KEY}-${k}`, JSON.stringify(v)); } catch {} },
  };
  const today = new Date().toISOString().slice(0, 10);
  const day = (store.get("day") || {}).date === today ? store.get("day") : { date: today, count: 0 };
  if (day.count >= DAY_CAP) { alert(`Daily limit reached (${DAY_CAP} pages for ${T.name} today). Continue tomorrow.`); return; }

  // The box on the page: status, Continue (for a check), Start (list mode), Stop.
  const state = window.kitRun = { stop: false, wake: () => {}, ctl: null };
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;top:8px;right:8px;z-index:2147483647;background:#fff;color:#000;border:2px solid #c00;" +
    "padding:8px 10px;font:14px sans-serif;box-shadow:0 2px 8px #0005;max-width:440px;white-space:pre-line";
  box.innerHTML = `<b>${T.name}</b> <span></span><textarea rows="6" cols="48" hidden placeholder="One URL per line"></textarea>` +
    '<div><button type="button" hidden>Start</button> <button type="button" hidden>Continue</button> <button type="button">Stop</button></div>';
  const [status] = box.getElementsByTagName("span"), [area] = box.getElementsByTagName("textarea");
  const [startBtn, goBtn, stopBtn] = box.getElementsByTagName("button");
  document.body.append(box);
  const show = s => { status.textContent = s; console.log(`${T.name}: ${s}`); };
  const finish = () => { delete window.kitRun; box.remove(); };
  // One timer per wait: a chain of short timers runs only once a minute in a hidden tab (Chrome "intensive throttling").
  const sleep = ms => new Promise(r => { const id = setTimeout(r, ms); state.wake = () => { clearTimeout(id); r(); }; });
  // Questions in the box, not confirm(): Chrome cancels confirm() when you switch to another tab.
  const ask = (msg, btn) => new Promise(r => {
    show(msg); btn.hidden = false;
    btn.onclick = () => { btn.hidden = true; r(true); };
    state.wake = () => { btn.hidden = true; r(false); };
  });
  stopBtn.onclick = () => { state.stop = true; stopBtn.disabled = true; stopBtn.textContent = "Stopping ..."; state.wake(); state.ctl?.abort(); };

  // What to read: numbered pages (T.pageUrl) or a list of URLs on this site (list mode).
  let urls = null;
  if (T.mode === "list") {
    area.hidden = false;
    if (!await ask("Paste the URLs (one per line, all on this site), then click Start.", startBtn)) { finish(); return; }
    area.hidden = true;
    const all = area.value.split(/\s+/).filter(Boolean);
    urls = all.filter(u => { try { return new URL(u, location.href).origin === location.origin; } catch { return false; } });
    if (urls.length < all.length) console.warn(`${all.length - urls.length} URL(s) are not on ${location.origin} and are left out (the browser does not allow it).`);
    if (!urls.length) { finish(); alert("No URL on this site in the list."); return; }
  }
  const saved = store.get("resume");
  const resumeAt = saved && (!urls || saved.total === urls.length) ? saved.next : 1;
  let n = +(prompt(`${T.name}: start at ${urls ? "URL number" : "page"}`, String(resumeAt)) || 0);
  if (!n) { finish(); return; }
  let last = urls ? urls.length : Infinity, delay = BASE_DELAY, errors = 0, tooMany = 0, runCount = 0, end = "";
  const started = Date.now(), files = [];

  const urlOf = i => urls ? new URL(urls[i - 1], location.href).href : new URL(T.pageUrl(i), location.href).href;
  const keyOf = i => `${urls ? "url" : "page"}-${String(i).padStart(4, "0")}.html`;
  const isChallenge = (r, t) => r.headers?.get("cf-mitigated") === "challenge" || /<title>\s*Just a moment/.test(t);
  let pages = {}, meta = {};
  const save = (blob, name) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    files.push(name);
    console.log(`%c${T.name}: downloaded ${name}`, "color: green");
  };
  const download = () => {
    const names = Object.keys(pages);
    if (!names.length) return;
    const from = names[0].slice(-9, -5), to = names.at(-1).slice(-9, -5);
    const body = { ...pages, _meta: { kit: KIT_VERSION, target: T.name, origin: location.origin, saved_at: new Date().toISOString(), urls: meta } };
    save(new Blob([JSON.stringify(body)], { type: "application/json" }), `${T.filePrefix || T.name}-${from}-${to}.json`);
    pages = {}; meta = {};
    store.set("resume", { next: +to + 1, total: urls ? urls.length : null });   // resume after the last page in a downloaded file
  };

  try {
    while (n <= last && !state.stop) {
      if (runCount >= MAX_PAGES) { end = `hard stop: ${MAX_PAGES} pages in this run. Paste again later to continue.`; break; }
      if ((Date.now() - started) / 60000 >= MAX_MINUTES) { end = `hard stop: ${MAX_MINUTES} minutes in this run. Paste again later to continue.`; break; }
      if (day.count >= DAY_CAP) { end = `hard stop: daily limit of ${DAY_CAP} pages reached. Continue tomorrow.`; break; }
      show(`${urls ? "URL" : "page"} ${n}${last < Infinity ? "/" + last : ""} ... (wait ${Math.round(delay / 1000)} s between pages)`);
      const url = urlOf(n), t0 = Date.now();
      let r, text = "", blob = null;
      state.ctl = new AbortController();                       // Stop, or no answer in 60 s, ends the request
      const signal = AbortSignal.any ? AbortSignal.any([state.ctl.signal, AbortSignal.timeout(60000)]) : state.ctl.signal;
      try {
        r = await fetch(url, { credentials: "include", cache: "no-store", signal });
        const type = r.headers.get("content-type") || "";
        if (urls && r.ok && !/text|html|json|xml/.test(type)) blob = await r.blob(); else text = await r.text();
      } catch (e) { r = { status: 0, headers: null }; }
      if (state.stop) break;
      const took = Date.now() - t0;

      if (isChallenge(r, text)) {
        download();
        if (!await ask(`Check ("Verify you are human") on ${url}\n1. Open that URL in a NEW tab.\n2. Tick the box there and wait for the page.\n3. Come back here and click Continue.`, goBtn)) break;
        continue;
      }
      if (r.status === 429 || r.status === 503) {              // the site asks us to slow down: wait longer each time, then stop
        if (++tooMany > MAX_429) { end = `hard stop: the site answered ${r.status} ${tooMany} times. Stop for today.`; break; }
        const after = +(r.headers?.get("retry-after") || 0) * 1000;
        const wait = Math.max(after, RETRY_MS * 2 ** (tooMany - 1));
        delay = Math.min(delay * 2, MAX_DELAY);
        show(`HTTP ${r.status}: the site asks to slow down. Wait ${Math.round(wait / 1000)} s (${tooMany}/${MAX_429}).`);
        await sleep(wait);
        continue;
      }
      if (r.status === 403) { end = `hard stop: the site refused (HTTP 403) ${url}. Do not retry today.`; break; }
      if (urls && (r.status === 404 || r.status === 410)) {     // a missing URL in a list: note it and go on
        meta[keyOf(n)] = { url, status: r.status }; pages[keyOf(n)] = ""; errors = 0;
        show(`HTTP ${r.status} on ${url}: not there, next`);
        if (n++ < last) await sleep(delay + Math.random() * JITTER);
        continue;
      }
      const hasData = urls ? (r.status === 200) : (r.status === 200 && T.hasData(text));
      if (!hasData && (urls || r.status !== 200 || n < last)) {    // an error: wait, retry, then stop
        if (++errors >= MAX_ERRORS) { end = `hard stop: ${url} failed ${MAX_ERRORS} times (HTTP ${r.status || "no answer"}). Paste again later.`; break; }
        show(`HTTP ${r.status || "no answer"} on ${url}: retry ${errors}/${MAX_ERRORS - 1} in ${Math.round(RETRY_MS / 1000)} s`);
        await sleep(RETRY_MS);
        continue;
      }
      if (!hasData) break;                                      // after the last page
      errors = 0; tooMany = 0;
      if (!urls) last = T.lastPage?.(text) || last;
      if (blob) {                                               // a PDF or another file: saved as it is, listed in the next JSON
        const base = decodeURIComponent(url.split("?")[0].split("/").pop() || "file").replace(/[^\w.-]+/g, "_").slice(-80);
        const name = `${T.filePrefix || T.name}-${String(n).padStart(4, "0")}-${base}`;
        save(blob, name);
        meta[keyOf(n)] = { url, file: name, bytes: blob.size, type: blob.type };
        pages[keyOf(n)] = "";
      } else {
        pages[keyOf(n)] = text;
        meta[keyOf(n)] = { url };
      }
      runCount++; day.count++; store.set("day", day); state.next = n + 1;
      if (Object.keys(pages).length >= CHUNK) download();
      // Adaptive speed: a slow answer doubles the wait (up to 60 s); a fast one brings it back to the base.
      delay = took > SLOW_MS ? Math.min(delay * 2, MAX_DELAY) : took < 3000 ? Math.max(BASE_DELAY, delay / 2) : delay;
      if (n++ < last) await sleep(delay + Math.random() * JITTER);
    }
  } finally {
    download();
    finish();
  }
  const list = files.length ? `\n\n${files.length} file(s) in this run:\n${files.slice(0, 30).join("\n")}${files.length > 30 ? "\n..." : ""}\n` +
    "If one is not in your Downloads folder, the browser blocked it: allow downloads for this site and run again from that page." : "";
  if (!end && n > last) { store.set("resume", null); end = "done. Send the files from your Downloads folder."; }
  alert(`${T.name}: ${end || `stopped before ${urls ? "URL" : "page"} ${n}. Paste the script again to continue from there.`}${list}`);
})();
