# jailbreak news captures — batch 1 (priority A items 1, 5-10, 12, 13, 15)

Capture date for every file: **2026-11-15** (UTC), Chromium via Playwright, live pages. All PNGs are >= 1600 px wide
(1808-2432 px; device scale factor 1.5-2). No browser chrome. Page content is not edited. Text on the page was not changed.
Things that were done to the page view are listed per file under "view".

Format: file | page URL | what is cropped | quoted text visible | view

## 1. Dopamine

- `01a-dopamine-3.0-release.png` | https://github.com/opa334/Dopamine/releases/tag/3.0 | release "3.0" title, meta line and full notes up to the DISCLAIMER |
  "Add Titan PPL/SPTM bypass by @alfiecg24, introduces support for all devices running 16.5.1 - 17.3.1" /
  "Add momentarius PPL bypass by @staturnzz and @TheRealClarity, introduces support for A12/A13 devices running 16.6 - 18.7.1, 26.0 - 26.0.1" |
  the page says "released this Aug 7" (no year shown). The small round avatar next to the author name is a logo-style icon, not a portrait.
- `01b-dopamine-readme.png` | https://github.com/opa334/Dopamine | README block only (sidebar and contributor avatars cropped out) |
  "A rootless semi-untethered jailbreak for iOS 15.0 - 17.3.1 (arm64e), iOS 15.0 - 18.7.1, 26.0 - 26.0.1 (A12/A13) and iOS 15.0 - 18.7.1 (arm64)." | none

## 5. 2015 "Rootless / iOS 9 jailbreak impossible" headlines

- `05a-dailysabah.png` | https://www.dailysabah.com/technology/2015/05/27/jailbreaking-apple-devices-to-be-impossible-with-ios-9 | headline + byline row |
  "Jailbreaking Apple devices to be impossible with iOS 9" (May 27, 2015) | a full-screen cookie-consent overlay was hidden with CSS only; nothing was accepted or clicked.
- `05b-ibtimes.png` | https://www.ibtimes.co.uk/apples-new-rootless-security-system-makes-ios-9-jailbreaking-impossible-1502662 | headline only |
  "Apple's new Rootless security system makes iOS 9 jailbreaking impossible?" | the headline is a question. The publish line ("Published 23 May 2015, 8:48 AM BST") sits next to the author's portrait, so it is cropped out;
  the date is from the page text. A full-screen consent dim layer was hidden with CSS only.
- `05c-ubergizmo.png` | https://www.ubergizmo.com/2015/05/ios-9-jailbreak-might-be-nearly-impossible | headline + byline |
  "iOS 9 Jailbreak Might Be Nearly Impossible" (05/24/2015 10:44 PDT) | none
- `05d-wccftech.png` | https://wccftech.com/ios-9-jailbreak-may-be-impossible/amp/ | headline + byline |
  "Apple's "Rootless" Security Feature May Halt iOS 9 Jailbreak" (May 23, 2015 at 12:07am EDT) | none. Softer wording ("May Halt").
- `05e-idownloadblog.png` | https://www.idownloadblog.com/2015/05/22/ios-9-security-jailbreak-rootless-not-impossible/ | headline + byline |
  "iOS 9 security & jailbreaking: there's no such thing as impossible" (May 22, 2015) | **this is the counter-view**, not a claim that it is impossible. Use it only if you want the "not so fast" beat.
- Redmond Pie: **not found.** The search did not return a Redmond Pie article on Rootless, so none is included.

## 6. Vice / Motherboard (2017-06-28)

- `06a-vice-headline.png` | https://www.vice.com/en/article/iphone-jailbreak-life-death-legacy/ | site header, headline, byline, date |
  "The Life, Death, and Legacy of iPhone Jailbreaking" - By Lorenzo Franceschi-Bicchierai and Brian Merchant - June 28, 2017, 12:02pm |
  the live page title is this one, not "iPhone Jailbreak: life, death, legacy" as in the brief. Only names are shown, no photos.
- `06b-vice-krstic.png` | same URL | two paragraphs around the Ivan Krstic quote |
  "Last year, Apple's head of security and jailbreak-killer-in-chief, Ivan Krstić, boasted about the strength of iOS's defenses, pointing to the fact that jailbreaks these days require "between five and ten distinct vulnerabilities in order to be able to defeat platform security mechanisms."" |
  **wording check:** the page says "between five and ten distinct vulnerabilities", not "5 to 10 separate bugs". The second paragraph (WWDC 2016 talk, "not been a single piece of iOS malware affecting our users at scale") is also visible.
  A membership pop-up was dismissed with its own "Or, continue for free" link before capture.

## 7. Brandon Azad, A12 PAC bypass (2019-02)

- `07-azad-pac-a12.png` | https://projectzero.google/2019/02/examining-pointer-authentication-on.html (the old googleprojectzero.blogspot.com URL redirects here) | title, date tag, first paragraph |
  "Examining Pointer Authentication on the iPhone XS" - 2019-FEB-01 - Brandon Azad; "...I then demonstrate a way to use an arbitrary kernel read/write primitive to forge kernel PAC signatures for the A keys, which is sufficient to execute arbitrary code in the kernel using JOP." |
  the site's cookie notice was dismissed with its "OK, got it" button.

## 8. checkm8 (2019-09)

- `08a-ipwndfu-readme.png` | https://github.com/axi0mX/ipwndfu | README top: tool title + checkm8 section (sidebar and avatars cropped out) |
  "checkm8 - permanent unpatchable bootrom exploit for hundreds of millions of iOS devices - meant for researchers, this is not a jailbreak with Cydia yet" | none
- `08b-macrumors.png` | https://www.macrumors.com/2019/09/27/checkm8-bootrom-exploit-iphones-ipads/ | headline, date line, first paragraph |
  "Checkm8 Exploit Opens Door to Unpatchable Jailbreak on iPhone 4S Through iPhone X" - Friday September 27, 2019 7:31 am PDT by Joe Rossignol | none
- `08c-thehackernews.png` | https://thehackernews.com/2019/09/bootrom-jailbreak-ios-exploit.html | headline + date |
  "Hacker Releases 'Unpatchable' Jailbreak For All iOS Devices, iPhone 4s to iPhone X" (Sep 27, 2019) | none

## 9. TrollStore

- `09-trollstore-readme.png` | https://github.com/opa334/TrollStore | README title + first paragraphs |
  "TrollStore is a permasigned jailed app that can permanently install any IPA you open in it. It works because of an AMFI/CoreTrust bug where iOS does not correctly verify code signatures of binaries in which there are multiple signers." / "Supported versions: 14.0 beta 2 - 16.6.1, 16.7 RC (20H18), 17.0" | none

## 10. Citizen Lab

- `10-citizenlab-mdd.png` | https://citizenlab.ca/research/million-dollar-dissident-iphone-zero-day-nso-group-uae/ (original /2016/08/ URL redirects here) | top hero / title block |
  "The Million Dollar Dissident - NSO Group's iPhone Zero-Days Used Against A UAE Human Rights Defender" | the publication date is not visible in this crop. The hero art shows company logos only, no portraits.

## 12. Apple Security Bounty

- `12-apple-bounty.png` | https://security.apple.com/bounty/ | hero section |
  "Apple Security Bounty - Rewards reaching $2 million - For exploit chains similar to those used in sophisticated, real-world attacks. And with bonuses, potential maximum rewards of over $5M." |
  the page shows no date, so the "2025-10 figures" in the brief cannot be confirmed from the capture. This is the live page on the capture date.

## 13. Securelist, Operation Triangulation

- `13-securelist-triangulation.png` | https://securelist.com/operation-triangulation/109842/ | headline + tag + date |
  "Operation Triangulation: iOS devices targeted with previously unknown malware" - APT REPORTS - 01 JUN 2023 | author avatars further down the page are not in the crop.

## 15. Apple Memory Integrity Enforcement

- `15-apple-mie.png` | https://security.apple.com/blog/memory-integrity-enforcement/ | blog header + first paragraph |
  "Memory Integrity Enforcement: A complete vision for memory safety in Apple devices" - September 9, 2025; "...We believe Memory Integrity Enforcement represents the most significant upgrade to memory safety in the history of consumer operating systems." | none

---

## NOT delivered, with the reason (nothing was substituted)

- **2. JailbreakMe 1.0 site / Installer.app screen** - web.archive.org is not reachable from this environment (TLS handshake is reset after ~10 s; archive.org itself works). The only Wikipedia image is a **JailbreakMe 3.0 (2010)** screenshot ("slide to jailbreak"), which is not 1.0, so it was not used. The Installer.app article only has a logo.
- **3. Cydia home screen (2008-2010 era)** - the only Commons screenshot found is "Cydia screenshot, OG.PNG": 640 x 1136, dated **7 August 2026** on the file page, i.e. a current Cydia, not the 2008-2010 UI. The original file download from upload.wikimedia.org was also rate-limited (HTTP 429). Not used.
- **4. evasi0n site (Feb 2013)** - archive.org snapshot only; web.archive.org is blocked here (see above).
- **11. Zerodium payout chart** - the live site returns 502 (TLS failure, as in the brief) and the archive is blocked. **Operation Zero price post (2023-09)** - the right URL was not identified yet.
- **14. Google Threat Intelligence "Coruna" (2026-03)** and **16. Calif / Hexacon blog (2026-10-16)** - not started; URLs not identified yet.
- **Priority B** - not started.
