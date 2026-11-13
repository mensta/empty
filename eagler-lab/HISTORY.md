# Eaglercraft — history, authorship and takedowns (research notes)

Method: web search + direct reading of primary/near-primary sources, 2026-11-12.
Reliability tags: **[primary]** the notice/page itself · **[press]** TorrentFreak reporting ·
**[weak]** fan/wiki/aggregator page (do not state as fact in a video) · **[unverified]** seen only in a search summary.
X (Twitter) could not be searched properly: no X search skill is available in this session, and
web search only returns account pages, not post contents. Nothing below comes from X posts.

## Who made it
- Created by **LAX1DUDE** (aka lax1dude). Credits page: JS runtime contributed by LAX1DUDE "from the
  beginning, with ayunami2000" [primary: eaglercraft.com/p/credits]. The credits page does NOT say who
  maintains it today, who the creator is by name, or who runs eaglercraft.com.
- Start date is inconsistent across sources (2020 vs 2021) [weak] — do not cite a year as fact.
- Other versions are credited elsewhere to community authors (1.12.2 port "by PeytonPlayz585" on the
  downloads page [primary]; the credits page spells names differently — check spelling before naming anyone).

## Dated events
| Date | Event | Source |
|---|---|---|
| 2023-02-22 | Mojang (Microsoft) DMCA notice to GitHub naming **92 repositories**, claiming copyright + trademark; says they are a remake of Minecraft 1.3 reusing its code/assets and "presumably decompiled and reverse engineered". | [press] [TorrentFreak 2023-02-24](https://torrentfreak.com/mojang-targets-repositories-of-browser-based-minecraft-copy-eaglercraft-230224/) |
| Feb 2023 | lax1dude removed code from his own site; kept a GitHub repo "EaglercraftX 1.8" with decompile tools/instructions; called the claim false ("Filing a false DMCA is illegal and immoral"). | [press] same |
| Spring 2023 | A Discord server and a GitLab account of a main developer shut down (identities not stated). | [press] [TorrentFreak 2023-04-24](https://torrentfreak.com/mojang-continues-crackdown-on-minecraft-pirates-230224/) |
| Apr 2023 | New GitHub wave against "hundreds" of Eaglercraft repos; GitHub removed all targeted. lax1dude later took the "EaglercraftX 1.8" repo offline too. Mojang asked Cloudflare to act on eaglercraft.ru (no result reported) and sent Google notices (homepage delisted). Mojang quote: "Exact source code or pixel perfect images do not need to be in the repo to constitute copyright infringement." | [press] same |
| 2024-01-08 | GitHub notice from Microsoft/Mojang AB vs. Eaglercraft repos: parent repos + forks, **363-repo network** per GitHub. Includes an **anti-circumvention** allegation (bypassing server auth / client-memory sign-in); GitHub said that claim was insufficient but other copyright claims were valid. Cites MINECRAFT trademark and 15 copyright registrations, plus the EULA. | [primary] [github/dmca](https://github.com/github/dmca/blob/master/2024/01/2024-01-08-mojang-2.md) |
| 2025-03-20 | Notice (sender name withheld) against one repo, `DustyDel/EaglerLauncher`, a launcher for Eaglercraft; lists claimed categories (code, textures, audio, branding, lore). | [primary] [github/dmca](https://github.com/github/dmca/blob/master/2025/03/2025-03-20-minecraft-3.md) |
| 2025-08-27 | eaglercraft.com pinned news item: site rewritten with modern web frameworks. | [primary-ish, via search summary] **[unverified]** |

Outcome of the 2024/2025 notices (what was actually removed) was not verified.

## Today (observed)
- eaglercraft.com says it is "an independent project, not affiliated with or endorsed by Mojang or
  Microsoft", provides *links* to community versions "for educational and archival purposes", and
  "do[es] not host games on our servers" [primary: /legal]. The offline zips I downloaded are served from
  `cdn.eaglercraft.net`; I did not check who owns that domain.
- The offline HTML itself says in its OpenGraph text: "this file is not a website, whoever uploaded it to
  this URL is a dumbass", and shows a launch countdown with the build date "10/17/2026" [verified].
- The game screen carries "Resources Copyright Mojang AB" [verified].

## Claims seen but NOT supported — keep out of the video as fact
- "1M+ students", "thousands of servers", FPS/WASM-GC percentages, "Microsoft ignores private use",
  "too decentralized to shut down" [weak: kwolfdaas hosting-guide history page, no sources].
- Nov 2022 as the first DMCA date [weak]; "Mojang asked lax1dude to collaborate / use his code" [weak].
- Anything about repositories being "repeatedly deleted and republished" beyond the sourced 2023 events.

## Gaps worth a deeper pass
1. Original text of the Feb 2023 and Apr 2023 GitHub notices (file names not located) and GitHub's response page.
2. Exact GitLab/Discord shutdown details and dates.
3. lax1dude's own public statements (primary posts) — not reachable via this search tool.
4. Current legal status/any court action; Mojang's stated policy toward browser ports.
5. Who owns/operates eaglercraft.com and cdn.eaglercraft.net, and how the 2026 downloads relate to the earlier removed repos.

## X (Twitter) investigation — relayed from the video session (not re-checked by me)
Reported by session `session_01868jCY66AR8bTz9BaEi3cv`, read-only, 2026-11-13. Full note lives in the
private repo `mensta/mv-studio`, branch `claude/eagler-explainer-plan`,
`projects/eagler/docs/history-x-notes.md` (commit f710ff8). I have NOT opened that file; this is the
session's own summary of it. The session itself says the search was unstable and not exhaustive.
- No post could be confirmed as written by lax1dude or ayunami2000. `@LAX1DUDE` and `@ayunami2000`
  showed 0 posts and cannot be called the people themselves **[unverified]**; `@lax1dude67` looks unrelated.
- No Mojang / Microsoft / Minecraft official-account post mentioning Eaglercraft turned up
  (an empty search result does not prove none exists).
- No first-hand post about the 2023 Discord / GitLab closures. One third-party post, `@uwunetes`
  2023-05-20, says they hosted a source archive, received a Mojang DMCA and would comply
  **[hearsay — not usable as fact]**.
- A German-language news article about the DMCA was shared on X on 2023-02-25 (only corroborates that
  the 2023-02 reporting existed). No lead on community events (shutdowns, revivals, moves).
- A third party's 2022 reply says it runs on TeaVM — hearsay; the build itself already shows this
  (see FINDINGS.md §5).
- Net result: **nothing from X is usable as a stated fact in the video.** Primary sources remain the
  GitHub DMCA notice originals and the project's own pages.
