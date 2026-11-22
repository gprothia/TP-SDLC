---
description: Turn a feature request (and any linked prototype) into an approved enterprise spec (rules in AGENTS.md)
---

# /write-spec

Usage: `/write-spec #<issue number>`. Follow `AGENTS.md`: section 0 (standards), 1b
(prototypes) and 2 (specs).

## 1. Gather
// turbo
1. Read the request and every comment: `gh issue view <n> --comments`.
2. Read `standards/README.md` and every standard it lists, `specs/_TEMPLATE.md`, and the
   existing specs in the same area (e.g. all `RSA-*`).
// turbo
3. `git checkout main && git pull`, then `git checkout -b feat/<id-lower>-<short-name>`.

## 2. If the issue links a prototype (its "Prototype" field), reverse-engineer it
4. Bring the prototype onto this branch as a reference. For a link like
   `.../tree/proto/<name>/prototypes/<name>`:
   `git fetch origin proto/<name>` then `git checkout FETCH_HEAD -- prototypes/<name>`.
5. Open `prototypes/<name>/index.html` in the browser. Click every button and link; capture a
   screenshot of each screen and state into `prototypes/<name>/screens/`.
6. Build an inventory, in a table, of everything the prototype shows or does:
   | Screen / element | What the user sees or does | Data behind it | Becomes |
   Every visible field is data (where does it come from, is it personal?); every button is an
   action (who may do it, is it audited?); every refresh or timer implies an API call (SLO).
7. Treat the prototype as evidence of **intent**, never as approval of **how**. Anything it
   does that a standard forbids or doesn't cover (e.g. a link anyone can open, a personal phone
   number on screen, data that refreshes every second) is **not copied silently**: it becomes
   an open question naming the standard rule (e.g. "AAA-1: does the share link need sign-in?").

## 3. Write the spec
8. Write `specs/<ID>-<short-name>.md` from the template, `status: draft`:
   - acceptance criteria from the request (and the prototype's inventory), with exact values;
   - every enterprise section filled from `standards/`: Security & access (AAA) with an
     Authorization table and audit events, Logging, API contract, SLO;
   - the control criteria they imply (403 per role not allowed, 404 for others' records, an
     audit event per change);
   - with a prototype, a `## Prototype reference` section: the link, the inventory table, and
     which criteria each element became;
   - every decision not in the issue or its comments under Open questions as `- [ ]`.
// turbo
9. `python scripts/check_spec.py specs/<file>`. Fix every error; review every warning.
10. Show the user the spec, the prototype inventory and the open questions, grouped as
    **business** (what members see) and **IT / security** (what the standards require). Wait.

## 4. Agree it
11. Apply the answers (tick each question with its answer), re-run step 9. When the user says
    the spec is agreed, set `status: approved` and commit `<ID>: add spec` (with the prototype
    files, as reference).
12. `git push -u origin HEAD`, so the spec can be linked and reviewed.
13. Draft a comment for the issue: a link to the spec on the branch and a short list of the
    decisions. Show it, and post it with `gh issue comment <n> --body-file ...` when the user
    agrees. Never edit the issue description.
14. Next step: `/build-spec specs/<file>`.
