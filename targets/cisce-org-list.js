// Target: a list of pages and PDFs on cisce.org (notices, circulars, statistics) that the Wayback Machine does not have.
// Paste the URL list into the box (one per line). PDFs are saved as they are; HTML pages go into cisce-org-NNNN-NNNN.json.
const TARGET = {
  name: "cisce-org",
  hosts: ["cisce.org", "www.cisce.org"],
  mode: "list",
  minDelayMs: 8000, maxPages: 300, maxMinutes: 90, dayCap: 500, chunk: 50,
};
