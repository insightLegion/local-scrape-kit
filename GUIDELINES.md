# Guidelines

These rules apply to every run and every change. They follow the s1d labs scraping rules (team docs 08 and 13).

## 1. When to use the kit

- Use it only when the team box, the scrape pool, the Indian proxies and the Wayback Machine cannot get the page.
- Use it only for public pages that any visitor sees without a login.
- Check the hub first: no other family must have the data (`select name from projects where settings->>'target' ilike '%host%'`).

## 2. Checks, captchas and logins

- You tick a check ("Verify you are human") yourself, in the browser, as a normal visitor.
- The scripts never click, solve or skip a check, a captcha or a login. Do not add code that does.
- Do not use a browser that a program controls (Playwright, Selenium, puppeteer) on a protected site. Such a browser fails
  the check, and it can look like an attack.
- Do not change the browser's identity (user agent, fingerprint) and do not use an anonymising proxy for these runs.

## 3. Speed

- One request at a time. 5 seconds or more between requests. Keep the defaults of the target.
- Do not run two scripts on the same site at the same time (two tabs or two people).
- Respect the hard stops. When a run stops with HTTP 429 or 403, stop for the day. Do not change the limits to go faster.
- Prefer quiet hours (night, India time) for long runs.

## 4. Data

- Keep the pages as the site gave them (no edits). Public data stays as published, including names on public pages.
- Do not save cookies, passwords or personal pages. The files contain only the pages of the run and their URLs.
- Send the files to trideep (or the box). Do not post them in public chats.
- Delete the local copies after they are on the box and in the bucket.

## 5. Changes to the kit

- Edit `engine.js` or `targets/*.js`, never `dist/*.js` by hand. Run `python build.py`. CI fails if `dist/` is out of date.
- Each change: a branch, a pull request, the `build` check green (tests in Edge and Firefox on Windows), then squash-merge.
- A new target needs a test with the local test site in `tests/test_kit.py` (its page layout, its last page).
- A bug: open an issue with the bug template (what the box said, the last page saved, the files in Downloads).
- Version: `KIT_VERSION` in `engine.js`; it goes into each file's `_meta`.

## 6. When something goes wrong

| What you see | What to do |
|---|---|
| The check comes back on every page | Stop. Try again another day, or from another network. Do not try to get past it. |
| "hard stop: the site answered 429" | Stop for today. |
| "hard stop: the site refused (HTTP 403)" | Stop. The site blocks this route. Tell trideep. |
| A file is not in Downloads | The browser blocked a download. Allow downloads for the site, paste again, type the first page of that file. |
| "Daily limit reached" | Continue tomorrow. |
