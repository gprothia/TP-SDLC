# Rate My Rescue

A clickable static prototype showing how AAA members can rate their roadside assistance experience and recognize great drivers.

## The idea in plain words

After (or even during) a roadside rescue, a member wants a quick, friendly way to say how it went and thank their driver:

1. **Rate a rescue (`"How did we do?"`)** — Pick 1 to 5 stars, tap quick feedback tags (**On time**, **Friendly driver**, **Explained the fix**), and optionally leave a short comment.
2. **My rescues list** — Pick any rescue from a list to rate it, including active rescues that are **still en route**.
3. **Thank-you confirmation** — Shows the submitted stars, tags, comment, and how the rating updates the driver's monthly average.
4. **Public `"Top drivers this month"` leaderboard** — Displays ranked drivers with their photo, truck unit, rescue count, top tag, and average star rating.

## Try it

Open `index.html` directly in any browser, or serve the folder locally:

```bash
python3 -m http.server 8000 --directory prototypes/rate-my-rescue
```

All data is fake and runs client-side with plain HTML, CSS, and JavaScript—no backend calls, no secrets, and no real personal data (`SPEC-2`).

## Screenshots

- [Rate a completed rescue](screens/01-rate-completed-rescue.png)
- [My rescues list (completed & en route)](screens/02-rescue-list.png)
- [Rate an en-route rescue](screens/03-rate-en-route-rescue.png)
- [Thank-you screen](screens/04-thank-you.png)
- [Top drivers this month leaderboard](screens/05-top-drivers-leaderboard.png)
