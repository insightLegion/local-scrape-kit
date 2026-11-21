// Target: any list of URLs on the site that is open in this tab (other sites are left out: the browser does not allow them).
// Use it for a site that blocks automated visits but shows its public pages to you. Slow on purpose.
const TARGET = {
  name: "url-list",
  mode: "list",
  minDelayMs: 8000, maxPages: 300, maxMinutes: 90, dayCap: 500, chunk: 50,
};
