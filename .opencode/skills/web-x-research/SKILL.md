---
name: web-x-research
description: Use when the user asks to research a topic on the web and on X (x.com, Twitter) without a search API - e.g. "web search and x.com to find how people do X", Japanese blog/Qiita/Zenn/GitHub/X posts about a technique, or reading a thread. Gives the routes that actually worked (FxTwitter API for X search and threads, Bing HTML, Qiita API, Zenn API, GitHub search) and the rules for reporting confidence. Not for questions answerable from the local code.
---

# Web + X research without a search tool

Use `webfetch` or `curl` from bash. `python` may be missing: use `python3`. Keep a pause of >= 1.5 s between calls to the same host.

## Routes that worked (verified 2026-11-12)

| Need | Route | Notes |
|---|---|---|
| X search | `https://api.fxtwitter.com/2/search?q=<q>&feed=top\|latest\|media&count=<=100` | No auth. Returns `results[].text/url/likes/author.screen_name/created_at`. Run both `top` and `latest`. Use `scripts/xsearch.py` (de-dupes, sorts by likes, filters). |
| One post / thread | `https://api.fxtwitter.com/2/status/{id}`, `/2/thread/{id}`, `/2/conversation/{id}` | `status.thread` can be null even when `/2/thread` returns the thread: call `/2/thread` too. `/2/conversation` is not in time order. |
| A user's posts | `/2/profile/{handle}/statuses?count=..&since=..` | `with_replies`, `groupthreads` are optional. |
| Web search | `https://www.bing.com/search?q=<urlencoded>&setlang=ja` | Works but results lean toward portals; DuckDuckGo (HTTP 202 challenge) and Brave (429) do not. Treat as a lead generator, not as evidence. |
| Qiita | `https://qiita.com/api/v2/items?query=<q>&per_page=20` | Output is huge: extract `title,url,likes_count,created_at` with python3. |
| Zenn | `https://zenn.dev/api/articles?q=<q>` | JSON. |
| GitHub repos | `https://api.github.com/search/repositories?q=<q>&sort=stars` | Unauthenticated, rate limited. Code search needs auth. |

FxTwitter's spec: `https://api.fxtwitter.com/2/openapi.json`. Documented limit is 1000 requests/min per IP; stay far below it.

## Workflow

1. Write 8-15 queries in the language of the people who post (Japanese for a Japanese topic): the plain topic, the tool names, the symptom words (403, 202, blocked), the practice words (自動化, 通知, GAS, Playwright), and "中の人"/professional wording when you want first-hand expertise.
2. Run X queries with `scripts/xsearch.py --out <file> --min-likes 2 --show 25 "q1" "q2" ...`. Posts that are the same text repeated by one account are bots/promotion: ignore.
3. Follow links from posts to the primary source (article, repo, official page) and read it. A post that only says "I did it" is a lead, not a method.
4. For parallel breadth (several topics, many pages), hand each topic to a subagent with a precise brief, the route table above, and a required output format. Do not duplicate their work.
5. Compare against the local code before recommending changes: say what the code already does, then list only the real gaps.

## Reporting rules

- Every claim carries its source URL. Mark confidence: **verified** (read the page/code/response) vs **snippet** (seen only in a search result or post).
- Say what you could not check (e.g. a terms-of-service page that returned 403) instead of filling the gap.
- **Verify values taken from other people's notes on the real system before putting them in code.** Example: an article gave CHINTAI sort=2 for "newest"; on the live site 2 was "cheapest first" and the real value was o=7. Check by loading the page with the parameter and reading which option of the sort control is selected.
- Do not use this to reach data behind a login, member-only systems, or private accounts.
