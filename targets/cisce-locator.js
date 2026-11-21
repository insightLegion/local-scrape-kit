// Target: every listing page of the CISCE school locator (about 335 pages of 10 schools).
// Files: cisce-pages-NNNN-NNNN.json ({"page-0001.html": html, ..., "_meta": {...}}), read by kit.py and by
// link/merge.py of github.com/s1d-labs/cisce-scraper.
const TARGET = {
  name: "cisce-locator",
  hosts: ["locate.cisce.org"],
  filePrefix: "cisce-pages",
  pageUrl: n => `/?page=${n}`,
  // card layout (2026) or table layout (2023-2025)
  hasData: t => /school-card|<li><b>[A-Z]{2,4}\d+<\/b><\/li>/.test(t),
  lastPage: t => { const m = t.match(/Showing\s+\d+\s+to\s+\d+\s+of\s+(\d+)\s+entries/); return m ? Math.ceil(+m[1] / 10) : null; },
  minDelayMs: 6000, maxPages: 400, maxMinutes: 120, dayCap: 800, chunk: 50,
};
