# local-scrape-kit

Saves public pages from sites that block automated visits, with your own browser, slowly, with hard stops.
For s1d labs work: the team box and the scrape pool cannot read these sites (an interactive "Verify you are human" check,
or a block of foreign and data-centre IP addresses). A person at a normal browser can.

Read [GUIDELINES.md](GUIDELINES.md) before the first run. The short form:

- You tick any check yourself. The scripts never click or solve a check, a captcha or a login.
- One page at a time, 5 seconds or more between pages, a page cap and a time cap per run, a daily cap.
- The script stops by itself when the site says "too many requests" (HTTP 429) three times, or refuses a page (HTTP 403).

## What is in it

| Script (`dist/`) | Site | What it saves |
|---|---|---|
| `cisce-locator.js` | locate.cisce.org | every listing page of the CISCE school locator (about 335 pages): `cisce-pages-NNNN-NNNN.json` |
| `cisce-org-list.js` | cisce.org | a list of pages and PDFs (notices, circulars) that you paste: `cisce-org-NNNN-NNNN.json` and the PDFs |
| `url-list.js` | any site | a list of URLs on the site of the open tab: `url-list-NNNN-NNNN.json` and the files |

`kit.exe` (or `python kit.py`) unpacks the downloaded files and makes `cisce_schools.csv` for the locator.

## Get it

- Windows: download the files from **Releases → latest**, or clone the repo:
  `git clone https://github.com/insightLegion/local-scrape-kit.git`
- Linux (Kubuntu): `git clone https://github.com/insightLegion/local-scrape-kit.git`. Use Firefox or Chrome. Run `python3 kit.py`.

## Run a script (example: the CISCE locator)

1. Open https://raw.githubusercontent.com/insightLegion/local-scrape-kit/main/dist/cisce-locator.js in your browser.
   Press Ctrl+A, then Ctrl+C. (Or open the file from your clone in a text editor.)
2. In your normal Chrome or Firefox, open https://locate.cisce.org/. Tick "Verify you are human" if it shows. Wait for the schools.
3. Press F12 and click **Console**. Paste with Ctrl+V and press Enter.
   - If the browser does not paste, type `allow pasting`, press Enter, then paste again.
4. A box asks for the start page. Click OK.
5. A red box at the top right shows the progress. You can use other tabs. Do not close this tab.
   - At the second file the browser asks about "multiple downloads". Click **Allow**.
6. If the check comes back, the red box says what to do: open the page in a new tab, tick the box there, come back, click **Continue**.
7. **Stop** ends the run at once and downloads what is not downloaded yet. Paste again later to continue from there.
8. At the end a message lists the files of the run. Check that they are in your Downloads folder.

For a list script (`cisce-org-list.js`, `url-list.js`): open the site first, paste the script, paste the URLs into the box
(one per line), click **Start**. URLs of other sites are left out (the browser does not allow them).

Ready lists: [`lists/cisce-org.txt`](lists/cisce-org.txt) has 86 cisce.org pages and PDFs (notices, the notice archive, WordPress
media lists) that the Wayback Machine does not have or has only as a 403 (list of 2026-11-21). Open https://cisce.org/ first.

## Unpack and check

- Windows: double-click `kit.exe`. SmartScreen can warn about an unknown app: click **More info → Run anyway**.
- Linux: `python3 kit.py` in the clone (Python 3.10 or newer, no other packages).

It reads the downloaded files from your Downloads folder and from its own folder and writes `kit-output/<script>/`:
`pages/`, `files/` (PDFs), `urls.csv`, and for the locator `cisce_schools.csv`. It lists missing pages and missing files.

## Send the files

Send the `*-NNNN-NNNN.json` files and the PDFs to trideep, or drag them into the VS Code file explorer of his team box.
On the box: the locator files go into `<data dir>/locator-<date>-saved-by-hand/` and `link/merge.py` of
[s1d-labs/cisce-scraper](https://github.com/s1d-labs/cisce-scraper) reads them.

## Hard stops and limits

| Limit | Value | Where |
|---|---|---|
| Time between pages | 5 s minimum on a real site (6-8 s for the locator, 8-10 s for lists), plus up to 2 s at random | `minDelayMs` in the target |
| Slow site | an answer that takes more than 10 s doubles the wait (up to 60 s) | engine |
| HTTP 429 / 503 | wait 2, 4, 8 minutes (or the site's Retry-After); the fourth time: stop | engine |
| HTTP 403 (not the check) | stop at once | engine |
| Errors | 5 failures of one page: stop | engine |
| Pages per run | 400 (locator), 300 (lists) | `maxPages` |
| Minutes per run | 120 (locator), 90 (lists) | `maxMinutes` |
| Pages per day per site | 800 (locator), 500 (lists) | `dayCap` (kept in the site's localStorage) |
| One run per tab | a second paste does not start a second run | engine |

## Add a site

Copy a file in `targets/`, change it, run `python build.py`, test it, open a pull request. See GUIDELINES.md.

## Tests

`python -m pytest tests -q` (needs `pip install pytest playwright` and `python -m playwright install chromium firefox`).
The tests run the scripts in a real browser against a local test site: a check, HTTP 429, 403, 404, a PDF, the Stop button,
each hard stop, and kit.py. CI runs them on Windows in Edge and Firefox on every push.
