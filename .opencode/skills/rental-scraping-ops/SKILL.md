---
name: rental-scraping-ops
description: Use when working on this rental-search repo's collection of Japanese rental listings (SUUMO, LIFULL HOME'S, at home, CHINTAI) - HOME'S returning 202 or empty pages, at home showing an auth page, incremental or new-arrival crawling, known_ids, run.py --incremental-others, or when asked about unlisted listings (未公開物件), REINS/ATBB, or smarter ways to hunt for a rental. Covers the practical methods, the hard limits, and what not to build.
---

# Rental listing collection: how it is done and where the line is

Read `AGENTS.md` (rules), `LESSONS.md` (symptom -> cause -> fix) and `HANDOFF.md` first. This skill adds what a 2026-11 survey of blogs, repos and X posts found, and what was verified on the live sites.

## What the community actually does (survey; sources and confidence marks in `references/survey-homes-scraping.md` and `references/survey-unlisted-reins-hunting.md`)

- Almost everyone parses list-page HTML with requests + BeautifulSoup. No hidden JSON/XHR API for HOME'S was found, and no case of parsing saved-search e-mails. Do not promise either.
- Pages are fetched newest-first and the crawl stops at the first page with nothing new (HOME'S `cond[sortby]=newdate`, at home `sort=33`, CHINTAI `o=7`; verified on the live sites by the selected option of the sort control).
- Seen IDs are stored with a first-seen date. The first run is a baseline (no notification). A run reporting more than ~10 "new" listings is treated as an anomaly. A page whose content hash did not change can skip parsing.
- Cross-site duplicates are removed by address + area + rent (+ layout). SUUMO is preferred.
- HOME'S 202 is treated as a soft throttle: back off (5 s x 1.8^n up to 60 s, ~6 tries), ~3-6 s between requests, <= 5 pages, the strictest area last, each area in its own try/except.
- Coverage is checked against the "N results" count shown on the page.
- Smaller, safer alternatives: official saved-search e-mail/LINE notifications on each portal; reading only pages the user opened (browser extension).

## What this repo does (use these, do not re-invent)

- `web.fetch_soup` + `web.Pacer`: retry on 202/empty/cut-off bodies, per-host gaps (HOME'S ~6 s), cookies cleared each request.
- `search_sites.collect`: a site that keeps failing is dropped for this run; the others continue. `incremental={site: known_urls}` crawls newest-first and stops at an all-known page.
- `known_ids.py`: state in `data/known_ids.json` (first_seen / last_seen / gone), `plan_incremental` (full crawl every 7 days because an incremental run cannot see removals), `merge_rows`, `update` (baseline, suspicious burst, failed sites never mark listings gone), `lifetimes` (days until removal: a rough popularity / decoy-ad signal).
- `python run.py --incremental-others` / `--full-others`. Tests: `python3 -m unittest discover -s tests`.

## Hard limits (observed)

- HOME'S: WAF challenge as HTTP 202 with an empty body; it comes more often the more you request, and can persist for minutes. At home: after a burst it returns HTTP 200 with a "認証中" puzzle page (0 listings). A retry loop cannot fix a persistent challenge; waiting can.
- **Never fetch the same site repeatedly just to test.** One or two requests per question, then stop. A burst of ~6 requests to at home in one session was enough to trigger the auth page.
- Do not add code that solves, evades or fakes the challenge (headless-browser tricks, fingerprint spoofing, CAPTCHA solving). A proxy only changes the route (`--proxy`), it does not pass the challenge. If a site stays blocked, report it and continue without it (HOME'S is optional).
- Terms: SUUMO's terms forbid use beyond private use, commercial use and interfering with operation. The HOME'S terms were not read (unverified). A hobby project that re-published data scraped from portals was shut down in 2021 (Comfy). Keep it personal, low-frequency, private repo, no sharing of images.

## REINS / ATBB / "unlisted" listings

- REINS (レインズ) and ATBB are member-only systems of licensed real-estate dealers (宅建業 license holders, via the dealer company). A 宅建士 certificate alone does not give access; employees use the company's ID for brokerage work. Rules forbid using them outside the dealer business and lending IDs.
- Do **not** build or suggest: using a dealer friend's login, scraping these systems, sharing credentials, or any bypass. If asked, explain why and offer the legitimate routes below.
- Legitimate routes: ask a brokerage (or a dealer acquaintance acting as your agent) to search REINS/ATBB for your conditions and send listings; services that introduce from dealer databases (e.g. ietty); UR (no key money or brokerage fee, condition e-mails); local brokerages and management companies directly; official saved searches on each portal.
- "Unlisted" mostly means pre-listing (先行募集), dealer-only, or only the owner/management company has it. Rentals have no legal duty to register on REINS (the duty is for sale/exchange under exclusive contracts), so rental info is spread by each listing company's choice. A pitch of "未公開あります" without rent/layout details is a lead-generation tactic.

## Hunting tips with the best support (X posts by agents and renters, 2026)

- Good rooms go in days, sometimes hours: shortlist several, confirm vacancy, view and apply without delay; apply to several if allowed.
- Decoy listings: the fair-competition code requires ads that exist, can be traded and are intended to be traded; online ads show a registration/last-update date and a next-update date (<= 2 weeks). Ask for current availability; "just got an application, how about this other one" is the typical bait.
- Timing: negotiation room until December, strong landlords in Jan-Mar. The brokerage fee cap for the tenant does not depend on advertising fees (AD).
- Use for the tool: `lifetimes` and first_seen dates to estimate how fast a listing disappears; official notifications in parallel with the crawl.
