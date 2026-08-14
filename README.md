# Guardrails for Kids — Design Spec

**Date:** 2026-08-11
**Status:** Approved design, updated with two rounds of gap analysis
**Deliverable:** A one-page, age-banded standard for children's AI use that a school or a family can adopt as-is.

## Problem

Kids reach for AI tools built for adults, and no shared standard exists for what good use looks like at a given age. Today every parent and every teacher improvises — one household, one classroom at a time. Nobody has a shared answer to what a nine-year-old should be allowed to do with AI, or a fifteen-year-old. The sharp end of the risk is real: AI systems engaging with children on self-harm, sexual content, and — increasingly — AI-generated sexual imagery of real kids.

## What we are building

— **"Using AI at Home and School, App "** — that:

- A principal can sign and a parent can stick on the fridge.
- Works for **both** home and school (one shared document, not separate versions).
- States, per age band, what is **allowed**, what the **adult checks**, and what the **tool must refuse**.
- Puts a non-negotiable safety floor above everything, at every age.
- Reads in plain language, stands on its own, needs no citations.

This is a **document project**. There is no software, no web app, no enforcement tooling. All the weight is on getting the content and structure right.

## Design decisions (settled)

| Decision | Choice |
|----------|--------|
| Core artifact | The standard document only — no software |
| Audience | One shared document for home *and* school |
| Age bands | Three: 8–11, 12–15, 16–18 |
| Structure | Flat per band. Three lenses (Allowed / Adult checks / Tool must refuse) |
| Safety floor | One "always, at every age" non-negotiables strip, above the grid |
| Voice | Plain-language, stands alone, no citations on the page |
| Adoption | Adult signature + date (no child co-sign) |
| Layout | 3×3 grid — bands as columns, lenses as rows |

## Research input folded in

Recent, well-established developments in kids + AI safety were incorporated into the content (sourced from general knowledge as of 2026, not a live feed — the live research engine requires Python 3.12+, which was unavailable in this environment):

- **Self-harm chatbot cases** (wrongful-death suits against Character.AI and OpenAI) → the universal self-harm line must not only refuse but **route to a named crisis line or trusted adult**.
- **Companion "AI friend" apps** (FTC 6(b) inquiry and California SB 243's requirement that companion bots disclose they are not human) → the tool must **always identify itself as an AI**. "No AI-friend apps" for 8–11. "Not a therapist" at 12–15.
- **AI-generated sexual imagery** ("nudify" apps, deepfake nudes of classmates, sextortion) → added to **both** the universal refusals **and** the adult-checks row.
- **Over-reliance / sycophancy** → light touch in the 12–15 and 16–18 adult-check rows.


1. **PII / data leakage (critical gap).** Kids do not understand what "personally identifiable information" means. They will casually type their full name, address, school name, phone number, or their parents' details into a chat window without recognizing it as a risk. Added to the universal strip as a tool refusal ("collecting or soliciting a child's personal information") and to every age band's adult-check row with age-appropriate framing.

2. **Inputs are not private — the tool remembers.** Children (and many adults) do not know that AI chat inputs may be stored, reviewed, or used for training. Added to adult-check rows: parents must tell kids that what they type is not a private diary entry.

3. **Guardrails fail — the adult is the real safety net.** Research confirms AI guardrails are trivially bypassable even by non-experts (The Register, August 2026, and Mozilla.ai benchmarking of open-source guardrails). The universal strip now explicitly says: "Guardrails are not walls — the adult is the real safety net."

4. **Secondhand exposure.** A child using AI safely can still see harmful AI-generated content shown to them by another child (a classmate passing around a deepfake, a friend showing an unfiltered chatbot conversation). Added to the 12–15 and 16–18 adult-check rows.

5. **AI-generated CSAM on major platforms.** Meta ran ads that contained AI-generated child sexual abuse imagery (Wired, August 2026, 325 points on Hacker News). This validates and sharpens the deepfake/nudify line — the risk is not hypothetical, it is already at platform scale.

6. **Regulatory pressure building.** A bipartisan US Senate hearing on August 6, 2026 introduced bills covering AI chatbot safety, online privacy for children, and AI-enabled toys — confirming the standard lands at the right moment and may align with forthcoming regulation.

7. **Uncensored / locally-run AI models (critical gap).** NPR reported in May 2026 on "AI models that are free, private, and will never say no" — open-source models (Llama, Mistral, etc.) that kids can download and run locally with zero safety filters. The entire "tool must refuse" framework assumes the tool HAS guardrails. A 14-year-old running an uncensored model on their laptop bypasses every refusal in the grid. Added to universal strip: "Not all AI tools have safety filters — only use tools the adult has checked." Added to 12–15 and 16–18 adult-check rows.

8. **AI-enabled toys and IoT devices.** The Guardian (March 2026) reported researchers calling for tighter regulation of AI toys for young children. These devices have microphones, cameras, and collect data in ways children cannot perceive. The spec previously only addressed software/AI chat — physical AI devices are a distinct PII vector. Added to the 8–11 adult-check row.

9. **AI-augmented search engines as a distinct risk vector.** PBS, the Japan Times, and the New York Post (all July 2026) covered a report finding Google's AI search features pose "unacceptable risks to kids" — surfacing harmful content through AI summaries rather than traditional search results. The spec lumped everything under "AI tools" but AI search is a distinct entry point that bypasses the "tool choice" gate. Added to adult-check rows: awareness that Google/Bing AI summaries are AI too.

10. **AI companion chatbots failing basic child safety tests.** The Transparency Coalition (April 2025) found that AI companion chatbots marketed as "safe" were "failing the most basic tests of child safety." The spec's "no AI friend apps" line for 8–11 is correct policy but incomplete: even supposedly vetted companion apps may fail. Added nuance to the 12–15 band.

11. **Platform-specific failures at major companies.** xAI's Grok was cited by TechCrunch as "among the worst we've seen" for child safety failures (including generating images of "minors in minimal clothing" per The Guardian, January 2026). Combined with the Meta CSAM ads finding (Wired, August 2026), the pattern is clear: major platforms with large safety teams are still shipping broken products. This validates keeping the universal strip's "Guardrails are not walls" language — and sharpens the urgency.

12. **State-level legislation emerging.** Oregon passed the first state-level chatbot protection laws for kids (January 2026). North Carolina introduced bipartisan AI-in-education guardrails (June 2026). Scotland published a children's rights + AI in schools framework (LSE, July 2026). The standard is not operating in a vacuum — it should align with and reference the emerging regulatory landscape (without citing specific laws on the printable page).

13. **Parental visibility into AI usage as an emerging product category.** School safety platforms are adding features that give parents visibility into their children's AI usage (PR Newswire, April 2026). This suggests the standard's adult-check row should explicitly mention visibility — not just "reviews history now and then" but a framework for what monitoring looks like at each age band.

14. **Educational refusal — "don't just say no."** A flat refusal without explanation teaches nothing and invites bypass attempts. Every age band's "tool must refuse" row now includes an educational response requirement: the tool must briefly explain WHY it refused in age-appropriate language, naming the real-world harm or consequence. At 8–11: "I can't do that because sharing your address could let strangers find you." At 12–15: "Making fake nude images of a classmate is abuse. Kids have been arrested and expelled." At 16–18: "That data can leak, be sold, or be used to impersonate you. Here is what happened to others."

15. **Learning-integrity education — "here's what you lose by skipping the work."** When a child asks AI to hand over answers instead of teaching them to think, the tool must explain the long-term cost of shortcutting learning. Added to the universal strip and to every age band's "What's allowed" row as an explicit behavioral requirement. At 8–11: "If I just tell you the answer, you won't learn how — and next time will be harder." At 12–15: "If I write it for you, you miss the practice your brain needs." At 16–18: "Submitting AI-generated work as yours risks academic discipline — and you graduate without the skills you paid to build."

## Page anatomy (top to bottom)

1. **Title + one-line purpose.** "Using AI at Home and School — A Family & School Standard," plus one sentence on what it is and who it's for.
2. **Universal strip — "Always, at every age."** Boxed/shaded, directly under the title, reads first. The non-negotiable safety floor.
3. **The 3×3 grid.** Columns = age bands (8–11 · 12–15 · 16–18). Rows = the three lenses. Read *down* a column for one child's age. Read *across* a row to see how each lens shifts as kids grow.
4. **Adoption footer.** One signature/date line for the adult, plus a short "how to use this" note.
5. **Version stamp.** `v1.0 · reviewed 2026-08` and a "review annually" note — a living standard, not a one-off flyer.

No logos, no images, no color dependence (works in black-and-white).

## Content

### Universal strip — "Always, at every age"

- The tool must always **identify itself as an AI** — never claim to be a person, a friend, or a counselor.
- The tool must always refuse to encourage, instruct, or roleplay **self-harm, suicide, or disordered eating** — and must **point the child to a named crisis line or a trusted adult**.
- The tool must always refuse any **sexual content with a child**, and any romantic/sexual roleplay.
- The tool must always refuse to generate — or help create or spread — **sexual or nude images of any real person**, including deepfake / "nudify" images of a classmate.
- The tool must always refuse to help a child **hide activity from a parent, meet an online stranger, or hand over identity, location, or contact details**.
- The tool must always refuse to **collect or solicit a child's personal information** — full name, address, school name, phone number, photos, or anything that could identify or locate them.
- **Not all AI tools have safety filters.** Open-source models can be downloaded and run without any guardrails. Children should only use tools the adult has checked.
- **Guardrails are not walls.** AI safety filters can fail or be bypassed. The adult is the real safety net.
- **When the tool refuses, it must briefly explain why** in age-appropriate language — not just say no. A child who understands the real-world reason is less likely to try to bypass it.
- **When a child asks for answers instead of learning, the tool must explain the long-term cost** — and guide them toward understanding instead. Skipping the work today means struggling harder tomorrow.
- **Adult's standing job:** the child knows AI can be wrong, knows an adult is reachable, and can bring any scary or upsetting reply to that adult *without getting in trouble.*

### The grid

|  | **8–11** | **12–15** | **16–18** |
|---|---|---|---|
| **What's allowed** | Use it *with* an adult nearby, on a shared/visible screen. Homework helper that *explains*, doesn't hand over answers. When asked to just give the answer, it says: "I can show you how to solve it, but if I just tell you, you won't learn how — and next time will be harder." Curiosity questions, reading & story help. Fun pictures on kid topics. | More independent use for schoolwork — brainstorming, checking understanding, feedback on their *own* writing. Looking things up. Skills practice, creative projects. When asked to do the work for them, it explains: "I can help you think through it, but if I write it for you, you miss the practice your brain needs." | Broad independent use for study, work, creativity, planning. Draft-then-edit their own work. Explore college/career. Treat it as capable but fallible. When asked to produce work to submit as their own, it explains: "Submitting AI-generated work as yours risks academic discipline — and you graduate without the skills you paid to build." |
| **What the adult checks** | Stays within earshot. Sets it up on the family/school account. Reviews history now and then. No "AI friend" companion apps. **No AI-enabled toys with microphones or cameras** unless the adult has verified what data they collect. Says out loud: *"AI makes things up — and it remembers what you type, so never tell it your name, address, or school."* | Agrees with the school where *help* ends and *cheating* begins. Occasional check-ins. Talks privacy — "your chat is not a diary, it's stored, don't share personal details or photos." Talks about **"it's not a therapist,"** and **deepfakes — making or sharing fake nude images of a real person is abuse and often a crime.** Warns that **some AI tools have no safety filters at all** — downloadable models, uncensored apps. Watches for secondhand exposure — a friend showing unfiltered AI content. | Shifts to coaching: integrity, sources, bias, healthy limits, **not over-relying on a tool that tends to agree with you.** Covers deepfakes / sextortion — and what to do if someone shows them AI-generated harmful content. Warns: "don't paste your resume, ID, or family info into a free AI tool — that data can leak." Warns that **not all AI has guardrails** — uncensored local models exist, and Google/Bing AI summaries are AI too. Agrees academic-honesty rules with the school. Stays reachable. |
| **What the tool must refuse** | Open-ended chat sold as a "friend." Anything scary, violent, or sexual. Collecting the child's personal info (name, address, school, photos). Acting alone — no purchases, no messaging strangers. **When it refuses, it says why in simple words:** "I can't do that because sharing your address could let strangers find you." | Romantic/sexual roleplay. Standing in for crisis mental-health care (must redirect to a human). Helping bypass school rules or age gates. Instructions for dangerous or illegal acts. Soliciting or storing personal identity details without a verified adult consent flow. **When it refuses, it names the real-world harm:** "Making fake nude images of a classmate is abuse. Kids have been arrested and expelled, and victims suffer real trauma." | Sexual content or self-harm help. Facilitating illegal activity. Enabling secret contact with strangers. Impersonating or creating deceptive content about real people. Collecting or inferring identity data without clear, age-appropriate disclosure of how it will be used. **When it refuses, it explains the lifelong consequences:** "That data can leak, be sold, or be used to impersonate you. Here is what happened to others who made the same mistake." |

### Adoption footer

> Adopted by ______________________ (parent / principal) · Date __________
> Post it where AI gets used. Revisit it once a year. Talk about the column that fits your child — and the row that changes as they grow.

### Version stamp

`v1.2 · reviewed 2026-08 · review annually`

## Design progression (why the grid works)

- The **"allowed" row loosens** left to right: supervised → independent → autonomous.
- The **"refuse" row stays strict**: the floor never drops. It only gets more specific with age.
- That across-row progression is the standard's answer to "what changes as they grow up" — the question nobody currently has a shared answer to.

## Files

- `standard/using-ai-at-home-and-school.md` — the clean, printable one-page standard (the artifact people adopt).
- `README.md` — this design spec.

Plain Markdown throughout: editable, diff-able, and it prints to one page without reflow surprises. The grid is the one table. Everything else is short lines.

## Adoption-readiness checklist ("testing" for a document)

1. **One-page test:** fits one printed page at readable size. If not, tighten cell wording — not structure.
2. **Fridge test:** a parent can grasp their child's column in under a minute.
3. **Principal test:** nothing a school would choke on — guidance, not legal claims.
4. **Sharp-end test:** the self-harm + crisis-routing line is unmissable, above the grid.
5. **Plain-language test:** no jargon. Every "refuse" item is concrete enough to tell whether a tool passed or failed it.
6. **PII test (new):** a child reading the 8–11 or 12–15 column (or having it read to them) understands "don't tell the AI your name, address, or school" — and the adult-check row prompts the conversation.
7. **Guardrail-failure test (new):** the universal strip does not promise that filters work perfectly — it names the adult as the real safety net.
8. **Uncensored-model test (new):** the universal strip warns that some AI tools have no safety filters. A parent reading the 12–15 or 16–18 column sees language about downloadable/uncensored models.
9. **AI-toys test (new):** the 8–11 adult-check row explicitly calls out AI-enabled toys with microphones or cameras — a distinct PII vector from chat.
10. **AI-search test (new):** the 16–18 adult-check row mentions that Google/Bing AI summaries are AI too — closing the "that's not AI, that's just Google" loophole.

## Out of scope

- Any software, app, browser extension, or automated enforcement.
- Separate home vs school versions.
- Citations, legal language, or a backing evidence appendix on the page.
- Child co-signature / pledge mechanics.
- Per-activity breakdowns within a band (kept flat by design).
