# jailbreak news captures - batches 1 and 2

Capture date for every file: **2026-11-15** (UTC), Chromium via Playwright, live pages. Widths: 1290-3200 px for page crops (device scale
factor 1.5-2, text is vector so it is sharp); `04b` is a small image and stays at its natural size, never upscaled.
No browser chrome. Page text and images are not edited. What was done to the *view* is listed per file ("view").
Batch 1 = items 1, 5-10, 12, 13, 15 (commit dd1bf08). Batch 2 (this commit) adds 04b, 11b, 14, 16 and priority B (`b01`-`b08`).

Format: file | page URL | what is cropped | quoted text visible | view / notes

## 1. Dopamine

- `01a-dopamine-3.0-release.png` | https://github.com/opa334/Dopamine/releases/tag/3.0 | release "3.0": title, meta line, notes up to the DISCLAIMER |
  "Add Titan PPL/SPTM bypass by @alfiecg24, introduces support for all devices running 16.5.1 - 17.3.1" /
  "Add momentarius PPL bypass by @staturnzz and @TheRealClarity, introduces support for A12/A13 devices running 16.6 - 18.7.1, 26.0 - 26.0.1" |
  the page says "released this Aug 7" (no year shown). The small round icon next to the author name is a logo-style avatar, not a portrait.
- `01b-dopamine-readme.png` | https://github.com/opa334/Dopamine | README block only (sidebar and contributor avatars cropped out) |
  "A rootless semi-untethered jailbreak for iOS 15.0 - 17.3.1 (arm64e), iOS 15.0 - 18.7.1, 26.0 - 26.0.1 (A12/A13) and iOS 15.0 - 18.7.1 (arm64)." | none

## 4. evasi0n (only part of it was possible)

- `04b-evasi0n-tool-screenshot.png` | https://en.wikipedia.org/wiki/Evasi0n | the article's infobox: screenshot of the **evasi0n tool 1.5.1 on OS X**, plus the Developers row |
  "evasi0n - Version 1.5.1 ... Welcome! evasi0n is an untethered jailbreak for iOS 6.0 through 6.1.2." / "evasi0n (c) 2013 @evad3rs" / "evasi0n 1.5.1 on OS X" |
  **This is the tool window, NOT the website with the download counter** (that needs an archive.org snapshot, see "not delivered"). Natural size, not upscaled (316 x 483 px).
  **Rights:** the screenshot is "Evasi0n jailbreak tool.png" on en.wikipedia, author "Screenshot by User:Kirbylover4000", a **non-free file used under Wikipedia's fair-use rationale for that article only**. Whether it may be used in the video is a rights call for the channel.
  The date is not stated on the file page; the "(c) 2013" line and the 1.5.1 version place it in 2013.

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
  "iOS 9 security & jailbreaking: there's no such thing as impossible" (May 22, 2015) | **this is the counter-view**, not a claim that it is impossible. Use it only for a "not so fast" beat.
- Redmond Pie: **not found.** The search returned no Redmond Pie article on Rootless.

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

## 11. Zerodium / Operation Zero (only news coverage was possible)

- `11b-securityweek-operationzero-coverage.png` | https://www.securityweek.com/russian-zero-day-acquisition-firm-offers-20-million-for-android-ios-exploits/ | headline + standfirst |
  "Russian Zero-Day Acquisition Firm Offers $20 Million for Android, iOS Exploits" - "Russian zero-day acquisition firm Operation Zero is now offering $20 million for full Android and iOS exploit chains." |
  **This is news coverage of the September 2023 announcement, NOT Operation Zero's own price post** (operationzero.org returns 502 from here). The article date (September 28, 2023) is on the page, next to the author's portrait, so it is cropped out.

## 12. Apple Security Bounty

- `12-apple-bounty.png` | https://security.apple.com/bounty/ | hero section |
  "Apple Security Bounty - Rewards reaching $2 million - For exploit chains similar to those used in sophisticated, real-world attacks. And with bonuses, potential maximum rewards of over $5M." |
  the page shows no date, so the "2025-10 figures" in the brief cannot be confirmed from the capture. This is the live page on the capture date.

## 13. Securelist, Operation Triangulation

- `13-securelist-triangulation.png` | https://securelist.com/operation-triangulation/109842/ | headline + tag + date |
  "Operation Triangulation: iOS devices targeted with previously unknown malware" - APT REPORTS - 01 JUN 2023 | author avatars further down the page are not in the crop.

## 14. Google Threat Intelligence Group, Coruna

- `14-gtig-coruna.png` | https://cloud.google.com/blog/topics/threat-intelligence/coruna-powerful-ios-exploit-kit | title, date, introduction |
  "Coruna: The Mysterious Journey of a Powerful iOS Exploit Kit" - March 3, 2026 - Google Threat Intelligence Group; "...has identified a new and powerful exploit kit targeting Apple iPhone models running iOS version 13.0 (released in September 2019) up to version 17.2.1 (released in December 2023). The exploit kit, named "Coruna" by its developers, contained five full iOS exploit chains and a total of 23 exploits." |
  the capture script hides large fixed-position overlays if the page shows any (not checked whether this page had one); the "Contact Us & Get a Demo" button in the left rail is page content.

## 15. Apple Memory Integrity Enforcement

- `15-apple-mie.png` | https://security.apple.com/blog/memory-integrity-enforcement/ | blog header + first paragraph |
  "Memory Integrity Enforcement: A complete vision for memory safety in Apple devices" - September 9, 2025; "...We believe Memory Integrity Enforcement represents the most significant upgrade to memory safety in the history of consumer operating systems." | none

## 16. Calif, Hexacon

- `16-calif-hexacon-iphone.png` | https://blog.calif.io/p/iphone | post title, subtitle, date, first line |
  "iPhone - Today, we hacked what we'd set out to hack: the iPhone." - OCT 16, 2026 - "Below is a series of demos we revealed at Hexacon in Paris today. Everything will be released in due time." |
  the post is titled just "iPhone"; this is the post found on the Calif newsletter for the Hexacon talk (date matches 2026-10-16). Site header cropped out.

## Priority B (reachable ones)

- `b01-checkra1n-site.png` | https://checkra.in/ | landing page top |
  "checkra1n - Jailbreak for iPhone 5s through iPhone X, iOS 12.0 and up - Get the beta now - Preliminary support for iOS 14 - read the announcement" | the page itself shows no date.
- `b02-palera1n-site.png` | https://palera.in/ | landing page top |
  "palera1n - Jailbreak for iPhone, iPad, Macbooks, and AppleTV's for versions 15 and higher - Compatibility with devices ranging from A8 to A11, and apple T2." | the terminal mock-up on the page lists contributor handles as plain text; no photos.
- `b03-geohot-unlock-2007.png` | https://www.electronicdesign.com/news/article/21777282/iphone-unlock-sparks-services-and-legal-issues | headline, standfirst, byline, date |
  "iPhone Unlock Sparks Services And Legal Issues" - Aug. 28, 2007 - "Since 17-year-old George Hotz of New Jersey announced he had successfully completed the world's first hardware-based iPhone unlock last Thursday, two other groups came up with software-based solutions for freeing the Apple device from AT&T's network." | a contemporary (2007) report; narrower crop to leave out the ad column.
- `b04-cydia-store-2009.png` | https://www.iphoneincanada.ca/2009/03/06/cydia-store-for-iphone-launches-today/ | headline + first paragraph |
  "Cydia Store for iPhone Launches Today" - "For those with jailbroken iPhones, Cydia is the place where you can download 3rd party applications that don't make it into the App Store." |
  the page shows a relative date ("18 years ago"); the date 2009-03-06 is from the URL path. Author name only (Gary Ng), no photo.
- `b05-apple-ios-6.1.3-security.png` | https://support.apple.com/en-us/103600 (HT202706 redirects here) | the "dyld" entry of "About the security content of iOS 6.1.3" |
  "dyld - Impact: A local user may be able to execute unsigned code - ... CVE-2013-0977 : evad3rs" | the crop shows the credit to evad3rs only; the advisory date (March 19, 2013, per Apple's security-announce list) is not in the crop.
- `b06-fugu14-readme.png` | https://github.com/LinusHenze/Fugu14 | README heading + first paragraph |
  "Fugu14 - Untethered iOS 14 Jailbreak - Fugu14 is an (incomplete) iOS 14 Jailbreak, including an untether (persistence), kernel exploit, kernel PAC bypass and PPL bypass." | sidebar and avatars cropped out.
- `b07-eu-dma-apple-newsroom.png` | https://www.apple.com/newsroom/2024/01/apple-announces-changes-to-ios-safari-and-the-app-store-in-the-european-union/ | press-release header |
  "PRESS RELEASE - January 25, 2024 - Apple announces changes to iOS, Safari, and the App Store in the European Union" | none
- `b08-japan-iclarified.png` | https://www.iclarified.com/99425/apple-opens-up-iphone-to-alternative-app-stores-and-browser-engines-in-japan | headline + first lines |
  "Apple Opens Up iPhone to Alternative App Stores and Browser Engines in Japan" - posted December 18, 2025 - "Apple has announced a broad set of changes to iOS, Safari, and the App Store in Japan as it moves to comply with the country's new Mobile Software Competition Act." | a news site, not Apple's own page (AppleInsider returned a bot-check 403 here).

---

## NOT delivered, with the reason (nothing was substituted)

- **2. JailbreakMe 1.0 site / Installer.app screen** - web.archive.org is not reachable from this environment (TLS handshake is reset after about 10 s; archive.org itself works). The only Wikipedia image is a **JailbreakMe 3.0 (2010)** screenshot ("slide to jailbreak"), which is not 1.0, so it was not used. The Installer.app article only has a logo.
- **3. Cydia home screen (2008-2010 era)** - both Commons screenshots ("Cydia screenshot, OG.PNG" and "Cydia screenshot, long.PNG") are dated **7 August 2026** on their file pages, i.e. a current Cydia. Not used. (The Commons original download is also rate-limited, HTTP 429.)
- **4. evasi0n website with the download counter (Feb 2013)** - needs an archive.org snapshot; blocked as above. `04b` shows only the tool window.
- **11. Zerodium payout chart** - the live site returns 502 (TLS failure, as in the brief) and the archive is blocked. **Operation Zero's own price post** - operationzero.org returns 502; only the news coverage (`11b`) is included.
- **Pangu9 site** - pangu.io returns 502 (the same TLS failure). Not captured.
- **usbliter8 repo (2026-06)** - the two GitHub URLs given in press coverage (prdgmshift/usbliter8, paradigmshift/usbliter8-poc) both return 404, so the repository was not identified.
- **Kaspersky slide about the six unknown hardware registers** - the slide is in the 37C3 talk, not on a page; Kaspersky's blog post about the talk has no such slide and does not state the number six. Not captured.
- **Redmond Pie** (item 5) - no matching article found.
