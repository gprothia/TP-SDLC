# Rate My Rescue

A clickable static prototype showing how AAA Roadside Assistance members could rate their rescue experience and celebrate top-performing drivers each month.

## The idea

After a roadside rescue, members should be able to give fast, lightweight feedback without filling out a long survey, and see which drivers are earning the highest praise from members across the fleet.

## What's in the prototype

1. **Rate a rescue ("How did we do?")** — Shows the selected rescue and driver details, an interactive 5-star selector, quick praise tags (**On time**, **Friendly driver**, **Explained the fix**), and an optional comment box.
2. **Any rescue in the list** — A side list of sample rescues lets you click and rate any rescue, including completed rescues and rescues whose truck is still **en route** (as well as editing an existing rating).
3. **Thank-you screen** — Confirms your submitted stars, tags, and comment, shows the driver's updated monthly average right away, and links directly to the leaderboard or the next unrated rescue.
4. **Public "Top drivers this month" leaderboard** — A public, no-sign-in view ranking drivers by average star rating with driver portrait photos, monthly review counts, praise-tag filters, recent member quotes, and live updates whenever you submit a rating.

## How to view

Open `index.html` directly in any browser — it uses plain static HTML, CSS, and JavaScript with fake data only and makes no backend calls.

## Screenshots

Captured in [`screens/`](./screens/):

- `01-rate-completed-rescue.png` — Screen 1: completed rescue (`#RSA-1042`) with "How did we do?", 5 stars, tags (**On time**, **Friendly driver**, **Explained the fix**), comment box, and the clickable rescues list.
- `02-thank-you.png` — Screen 2: thank-you confirmation screen after submitting a rating, with the driver's updated monthly average.
- `03-top-drivers-leaderboard.png` — Screen 3: public "Top drivers this month" leaderboard with driver photos, average stars, and live updated standings.
- `04-rate-en-route-rescue.png` — Rating an **en route** rescue (`#RSA-1048`) picked from the list while the truck is still on the way.
