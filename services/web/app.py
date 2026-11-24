"""Roadside Assistance member and dispatcher portal (demo for AAA).

Pages
  /signin             demo sign-in: pick a member or the dispatcher (stands in for company SSO)
  /requests/new       RSA-001  a member asks for help
  /requests           RSA-002  members see their own requests; dispatchers see all
  /requests/{id}      RSA-002/003  details; dispatchers update status, ETA and driver

The browser only talks to this server. It calls the API server-side, passing the signed-in
user's token. On Cloud Run the API is private: calls also carry a Google identity token for
the API's audience in X-Serverless-Authorization, leaving Authorization for the app's token.
"""

from __future__ import annotations

import asyncio
import html
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

API_URL = os.environ.get("API_URL", "http://localhost:8080")
API_AUDIENCE = os.environ.get("API_AUDIENCE", "")
COOKIE = "session"


class GoogleIdTokenAuth(httpx.Auth):
    """Cloud Run IAM for the private API: an identity token in X-Serverless-Authorization."""

    def __init__(self, audience: str):
        self.audience, self._token, self._expires = audience, "", 0.0

    async def _get(self) -> str:
        if time.time() > self._expires:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2 import id_token

            self._token = await asyncio.to_thread(id_token.fetch_id_token, GoogleRequest(), self.audience)
            self._expires = time.time() + 45 * 60
        return self._token

    async def async_auth_flow(self, request):
        request.headers["X-Serverless-Authorization"] = f"Bearer {await self._get()}"
        yield request


app = FastAPI(title="Roadside Assistance")
client = httpx.AsyncClient(base_url=API_URL, timeout=10, auth=GoogleIdTokenAuth(API_AUDIENCE) if API_AUDIENCE else None)

HELP_TYPES = {
    "tow": "Tow",
    "battery": "Battery jump-start",
    "flat_tyre": "Flat tyre",
    "lockout": "Locked out",
    "fuel": "Out of fuel",
}
STATUS_LABEL = {
    "received": "Received",
    "assigned": "Truck assigned",
    "en_route": "On the way",
    "arrived": "Arrived",
    "completed": "Completed",
    "cancelled": "Cancelled",
}
NEXT_STATUS = {"received": "assigned", "assigned": "en_route", "en_route": "arrived", "arrived": "completed"}
TRACKER_STEPS = [
    ("received", "Received"),
    ("assigned", "Truck assigned"),
    ("en_route", "On the way"),
    ("arrived", "Arrived"),
]
CANCELLABLE_STATUSES = {"received", "assigned", "en_route"}
RATING_TAGS = ("On time", "Friendly driver", "Explained the fix")
DRIVERS_STATIC_DIR = Path(__file__).resolve().parent / "static" / "drivers"

CSS = """
*{box-sizing:border-box}
body{font-family:Roboto,Arial,sans-serif;margin:0;color:#202124;background:#F8F9FA}
header{background:#0B3D91;color:#fff;padding:14px 32px;display:flex;align-items:center;gap:24px}
header .brand{font-weight:700;font-size:18px;margin-right:auto}
header a{color:#fff;text-decoration:none}
header .who{font-size:14px;opacity:.9}
main{max-width:860px;margin:32px auto;padding:0 16px}
.card{background:#fff;border:1px solid #DADCE0;border-radius:12px;padding:24px;margin-bottom:16px}
h1{font-size:28px;font-weight:500;margin:0 0 16px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid #E8EAED}
label{display:flex;flex-direction:column;gap:6px;font-size:14px;margin-bottom:14px}
input,select{padding:9px;border:1px solid #DADCE0;border-radius:8px;font-size:15px}
button{padding:10px 18px;border-radius:8px;border:0;background:#0B3D91;color:#fff;font-size:15px;cursor:pointer}
.users{display:flex;gap:12px;flex-wrap:wrap}
.badge{display:inline-block;padding:3px 12px;border-radius:12px;background:#E8F0FE;color:#174EA6;font-size:14px}
.error{color:#C5221F}
.muted{color:#5F6368;font-size:14px}
.demo{font-size:12px;color:#5F6368;text-align:center;margin:24px}
.eta-hero{background:linear-gradient(135deg,#0B3D91 0%,#1452B8 100%);color:#fff;border:0}
.eta-hero.arrived{background:linear-gradient(135deg,#137333 0%,#1E8E3E 100%)}
.eta-hero.cancelled{background:linear-gradient(135deg,#4B5563 0%,#6B7280 100%)}
.eta-big{font-size:44px;font-weight:800;line-height:1.1;margin:8px 0}
.stepper{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}
.step{text-align:center;font-size:13px;color:#5F6368}
.step .dot{width:30px;height:30px;border-radius:50%;border:2px solid #DADCE0;display:inline-flex;
align-items:center;justify-content:center;font-weight:700;margin-bottom:6px;background:#fff}
.step[data-state="done"] .dot{background:#0B3D91;border-color:#0B3D91;color:#fff}
.step[data-state="active"] .dot{background:#E8F0FE;border-color:#0B3D91;color:#0B3D91}
.step[data-state="active"]{color:#0B3D91;font-weight:700}
.map-box{border:1px solid #DADCE0;border-radius:10px;overflow:hidden;background:#EDF2FA}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.btn-secondary{background:#F3F7FD;color:#0B3D91;border:1px solid #C8D9F6}
.btn-danger{background:#fff;color:#C5221F;border:1px solid #F5C2C0}
.btn-danger-solid{background:#C5221F;color:#fff}
dialog{border:0;border-radius:12px;padding:22px;max-width:400px;width:90%;box-shadow:0 12px 30px rgba(0,0,0,.2)}
dialog::backdrop{background:rgba(15,23,42,.48)}
.toast-msg{margin-top:10px;font-size:14px;color:#137333;font-weight:600}
.star-row{display:flex;gap:8px;margin:12px 0}
.star-btn{background:#F1F3F4;color:#5F6368;border:1px solid #DADCE0;font-size:22px;padding:8px 14px;border-radius:10px}
.star-btn[aria-checked="true"]{background:#FEF7E0;color:#B06000;border-color:#F9AB00}
.tag-row{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 16px}
.tag-btn{background:#F8F9FA;color:#202124;border:1px solid #DADCE0;border-radius:999px;padding:7px 14px;font-size:14px}
.tag-btn.active,.tag-btn[aria-pressed="true"]{background:#E8F0FE;color:#0B3D91;border-color:#0B3D91;font-weight:600}
textarea{width:100%;padding:10px;border:1px solid #DADCE0;border-radius:8px;
  font-size:15px;font-family:inherit;min-height:84px}
.driver-avatar{width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid #E8F0FE;flex-shrink:0}
.driver-initials{width:52px;height:52px;border-radius:50%;background:#E8F0FE;color:#0B3D91;display:inline-flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
.standing-item{display:flex;align-items:center;justify-content:space-between;
  gap:14px;padding:14px 0;border-bottom:1px solid #E8EAED}
.standing-left{display:flex;align-items:center;gap:12px}
.standing-right{text-align:right;white-space:nowrap}
.pill-link{display:inline-block;padding:6px 14px;border-radius:999px;border:1px solid #DADCE0;
  background:#fff;color:#202124;text-decoration:none;font-size:14px}
.pill-link.active{background:#0B3D91;color:#fff;border-color:#0B3D91}
"""


def page(title: str, body: str, user: dict | None = None) -> HTMLResponse:
    who = ""
    if user:
        who = (
            f'<span class="who" data-testid="signed-in-as">Signed in as {html.escape(user["name"])} '
            f'({html.escape(user["role"])})</span><a href="/signout">Sign out</a>'
        )
    nav = ""
    if user and user["role"] == "member":
        nav = (
            '<a href="/requests/new">Request help</a>'
            '<a href="/requests">My requests</a>'
            '<a href="/leaderboard">Top drivers this month</a>'
        )
    elif user:
        nav = '<a href="/requests">All requests</a>'
    return HTMLResponse(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header><span class="brand">Roadside Assistance</span>{nav}{who}</header>
<main>{body}</main>
<p class="demo">Demo application. Not an AAA product. Sample data only.</p>
</body></html>"""
    )


def auth_headers(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    return {"Authorization": f"Bearer {token}"} if token else {}


async def signed_in(request: Request) -> dict | None:
    if not request.cookies.get(COOKIE):
        return None
    r = await client.get("/v1/me", headers=auth_headers(request))
    return r.json() if r.status_code == 200 else None


def to_signin() -> RedirectResponse:
    return RedirectResponse("/signin", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
async def home(request: Request):
    return RedirectResponse("/requests" if await signed_in(request) else "/signin", status_code=303)


# --------------------------------------------------------------------------- sign-in (demo SSO)


@app.get("/signin")
def signin_page():
    people = [("alice", "Alice Ng", "member"), ("bob", "Bob Ortiz", "member"), ("dana", "Dana Kim", "dispatcher")]
    buttons = "".join(
        f'<form method="post" action="/signin"><input type="hidden" name="user" value="{u}">'
        f'<button type="submit">Sign in as {n} ({r})</button></form>'
        for u, n, r in people
    )
    return page(
        "Sign in",
        f"""<div class="card"><h1>Sign in</h1>
<p class="muted">Demo sign-in. In production this is the company identity provider.</p>
<div class="users">{buttons}</div></div>""",
    )


@app.post("/signin")
async def signin(user: str = Form(...)):
    r = await client.post("/v1/auth/demo-login", json={"user": user})
    if r.status_code != 200:
        failed = page("Sign in", '<div class="card"><p class="error" role="alert">Sign-in failed</p></div>')
        failed.status_code = 502  # the API refused or couldn't be reached
        return failed
    resp = RedirectResponse("/requests", status_code=303)
    resp.set_cookie(COOKIE, r.json()["token"], httponly=True, samesite="lax")
    return resp


@app.get("/signout")
def signout():
    resp = RedirectResponse("/signin", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


# --------------------------------------------------------------------------- RSA-001 request help


@app.get("/requests/new")
async def new_request(request: Request):
    user = await signed_in(request)
    if not user:
        return to_signin()
    options = "".join(f'<option value="{k}">{v}</option>' for k, v in HELP_TYPES.items())
    return page(
        "Request help",
        f"""<div class="card"><h1>Request roadside help</h1>
<form method="post" action="/requests">
<label>What do you need?<select name="type">{options}</select></label>
<label>Where are you?<input name="location" required></label>
<label>Phone number<input name="phone" required></label>
<button type="submit">Send request</button>
</form></div>""",
        user,
    )


@app.post("/requests")
async def submit_request(request: Request, type: str = Form(...), location: str = Form(...), phone: str = Form(...)):
    r = await client.post(
        "/v1/requests", json={"type": type, "location": location, "phone": phone}, headers=auth_headers(request)
    )
    if r.status_code == 401:
        return to_signin()
    if r.status_code != 201:
        user = await signed_in(request)
        detail = "; ".join(e["message"] for e in r.json().get("errors", [])) or r.json().get("message", "")
        return page(
            "Request help",
            f'<div class="card"><p class="error" role="alert">Could not send: {html.escape(detail)}</p>'
            '<a href="/requests/new">Try again</a></div>',
            user,
        )
    return RedirectResponse(f"/requests/{r.json()['id']}?created=1", status_code=303)


# --------------------------------------------------------------------------- RSA-002 view requests


@app.get("/requests")
async def list_requests(request: Request):
    user = await signed_in(request)
    if not user:
        return to_signin()
    rows = (await client.get("/v1/requests", headers=auth_headers(request))).json()
    title = "My requests" if user["role"] == "member" else "All requests"
    member_col = "<th>Member</th>" if user["role"] == "dispatcher" else ""
    body = "".join(
        f'<tr><td><a href="/requests/{r["id"]}">{r["id"]}</a></td>'
        + (f"<td>{html.escape(r['member'])}</td>" if user["role"] == "dispatcher" else "")
        + f"<td>{HELP_TYPES[r['type']]}</td><td>{html.escape(r['location'])}</td>"
        f"<td>{STATUS_LABEL[r['status']]}</td></tr>"
        for r in rows
    )
    empty = '<p class="muted">No requests yet.</p>' if not rows else ""
    return page(
        title,
        f"""<div class="card"><h1>{title}</h1>
<table aria-label="Requests"><thead><tr>
<th>Request</th>{member_col}<th>Help</th><th>Location</th><th>Status</th></tr></thead>
<tbody>{body}</tbody></table>{empty}</div>""",
        user,
    )


def _step_state(step_key: str, status: str) -> str:
    order = [k for k, _ in TRACKER_STEPS]
    if status not in order:
        return "pending"
    cur_idx, step_idx = order.index(status), order.index(step_key)
    if step_idx < cur_idx or (status == "arrived" and step_idx == cur_idx):
        return "done"
    return "active" if step_idx == cur_idx else "pending"


def _progress_tracker_html(r: dict) -> str:
    hist = {h["status"]: h["at"] for h in r.get("history", [])}
    items = []
    for i, (key, label) in enumerate(TRACKER_STEPS, start=1):
        state = _step_state(key, r["status"])
        mark = "✓" if state == "done" else str(i)
        at = html.escape(hist.get(key, "—")[-8:]) if key in hist else "—"
        items.append(
            f'<div class="step" data-testid="step-{key}" data-state="{state}">'
            f'<div class="dot">{mark}</div><div>{label}</div><div class="muted">{at}</div></div>'
        )
    return (
        '<div class="card"><h2>Rescue Progress</h2>'
        f'<div class="stepper" data-testid="progress-tracker">{"".join(items)}</div></div>'
    )


def _live_map_html(r: dict) -> str:
    progress_by_status = {"received": 0.1, "assigned": 0.25, "en_route": 0.6, "arrived": 1.0}
    frac = progress_by_status.get(r["status"], 0.15)
    tx = round(80 + frac * (540 - 80), 1)
    ty = round(180 - frac * (180 - 72), 1)
    return f"""<div class="card"><h2>Live Map</h2>
<div class="map-box" data-testid="live-map">
<svg viewBox="0 0 640 220" style="display:block;width:100%;height:200px" aria-label="Live rescue map">
  <rect x="0" y="0" width="640" height="220" fill="#E8EFFA"/>
  <path d="M 80 180 L 540 72" stroke="#93B4E8" stroke-width="6" stroke-dasharray="10 8" fill="none"/>
  <path d="M 80 180 L {tx} {ty}" stroke="#0B3D91" stroke-width="6" fill="none"/>
  <g transform="translate(540,72)"><circle r="10" fill="#0B3D91" stroke="#fff" stroke-width="3"/>
    <text x="0" y="-18" text-anchor="middle" fill="#0B3D91" font-size="12" font-weight="700">You</text></g>
  <g data-testid="truck-marker" transform="translate({tx},{ty})">
    <rect x="-18" y="-13" width="36" height="26" rx="7" fill="#fff" stroke="#0B3D91" stroke-width="2.5"/>
    <text x="0" y="5" text-anchor="middle" font-size="15">🚚</text></g>
</svg></div></div>"""


def _live_tracking_html(r: dict, user: dict) -> str:
    status = r["status"]
    hero_cls = "arrived" if status == "arrived" else ("cancelled" if status == "cancelled" else "")
    if status == "cancelled":
        eta_big, eta_sub = "Cancelled", "This roadside assistance request has been cancelled."
    elif status == "arrived":
        eta_big, eta_sub = "Here!", "Your driver has arrived at your location."
    elif r.get("eta_minutes") is not None:
        eta_big = f"{r['eta_minutes']} min away"
        eta_sub = f"Refreshes automatically every 2 minutes &bull; {html.escape(r['location'])}"
    else:
        eta_big, eta_sub = "Assigning driver...", f"We are finding the closest truck near {html.escape(r['location'])}."

    d_name = html.escape(r.get("driver_name") or r.get("driver") or "Assigning soon")
    d_truck = html.escape(r.get("driver_truck") or "Pending assignment")
    d_rating = f"★ {r['driver_rating']}" if r.get("driver_rating") else "—"
    d_phone = html.escape(r.get("driver_phone") or "Not yet available")
    # RSA-005: partner verification badge
    if r.get("driver_verified") is True:
        badge = '<span class="badge" data-testid="driver-verified">✔ Verified driver</span>'
    elif r.get("driver_verified") is False:
        badge = '<span class="muted" data-testid="driver-unverified">Verification pending</span>'
    else:
        badge = ""
    can_cancel = user["role"] == "member" and status in CANCELLABLE_STATUSES
    cancel_btn = (
        '<button type="button" class="btn-danger" id="openCancelBtn">Cancel Rescue Request</button>'
        if can_cancel
        else ""
    )
    rate_btn = ""
    if user["role"] == "member" and status == "completed" and r.get("driver_name"):
        label = "View submitted rating" if r.get("rating") else "Rate this rescue"
        rate_btn = f'<a href="/requests/{r["id"]}/rate"><button type="button">{label}</button></a>'

    return f"""<div class="card eta-hero {hero_cls}" data-testid="refresh-interval" data-refresh-ms="120000">
  <div>Live Rescue Tracking</div>
  <div class="eta-big" data-testid="live-eta">{eta_big}</div>
  <div>{eta_sub}</div>
</div>
{_progress_tracker_html(r)}
{_live_map_html(r)}
<div class="card">
  <h2>Your Rescue Driver</h2>
  <p><strong data-testid="driver-name">{d_name}</strong> &bull; <span data-testid="driver-rating">{d_rating}</span></p>
  <p class="muted" data-testid="driver-truck">{d_truck}</p>
  <p>{badge}</p>
  <p data-testid="driver-phone">Phone: {d_phone}</p>
  <div class="actions">
    <button type="button" id="callDriverBtn">Call Driver</button>
    <button type="button" class="btn-secondary" id="shareLinkBtn">Share Live Link</button>
    {rate_btn}
    {cancel_btn}
  </div>
  <div id="shareToast" class="toast-msg" aria-live="polite"></div>
</div>
<dialog id="callDialog"><h3>Calling {d_name}</h3><p>Phone: <strong>{d_phone}</strong></p>
  <button type="button" id="closeCallBtn">Close</button></dialog>
<dialog id="cancelDialog"><h3>Cancel your rescue?</h3><p>Are you sure you want to cancel request {r["id"]}?</p>
  <form method="post" action="/requests/{r["id"]}/cancel" style="display:flex;gap:10px;justify-content:flex-end">
    <button type="button" class="btn-secondary" id="keepWaitingBtn">Keep Waiting</button>
    <button type="submit" class="btn-danger-solid">Yes, Cancel</button>
  </form></dialog>
<script>
(() => {{
  setInterval(() => window.location.reload(), 120000);
  const callBtn = document.getElementById("callDriverBtn");
  const callDlg = document.getElementById("callDialog");
  const closeCall = document.getElementById("closeCallBtn");
  if (callBtn && callDlg) callBtn.addEventListener("click", () => callDlg.showModal());
  if (closeCall && callDlg) closeCall.addEventListener("click", () => callDlg.close());
  const shareBtn = document.getElementById("shareLinkBtn");
  const shareToast = document.getElementById("shareToast");
  if (shareBtn && shareToast) shareBtn.addEventListener("click", () => {{
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(window.location.href).catch(() => {{}});
    }}
    shareToast.setAttribute("role", "status");
    shareToast.textContent = "Live tracking link copied! Sign-in is required to view.";
  }});
  const openCancel = document.getElementById("openCancelBtn");
  const cancelDlg = document.getElementById("cancelDialog");
  const keepBtn = document.getElementById("keepWaitingBtn");
  if (openCancel && cancelDlg) openCancel.addEventListener("click", () => cancelDlg.showModal());
  if (keepBtn && cancelDlg) keepBtn.addEventListener("click", () => cancelDlg.close());
}})();
</script>"""


@app.get("/requests/{request_id}")
async def show_request(request: Request, request_id: str, created: int = 0):
    user = await signed_in(request)
    if not user:
        return to_signin()
    resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
    if resp.status_code != 200:
        return page("Not found", '<div class="card"><h1>Request not found</h1></div>', user)
    r = resp.json()
    banner = '<p class="badge" role="status">Help is on the way. We received your request.</p>' if created else ""
    eta = f"{r['eta_minutes']} min" if r["eta_minutes"] is not None else "Not yet known"
    driver = html.escape(r["driver"]) if r["driver"] else "Not yet assigned"
    update = ""
    if user["role"] == "dispatcher" and r["status"] in NEXT_STATUS:
        nxt = NEXT_STATUS[r["status"]]
        update = f"""<div class="card"><h1>Update request</h1>
<form method="post" action="/requests/{r["id"]}/update">
<label>Next status<select name="status"><option value="{nxt}">{STATUS_LABEL[nxt]}</option></select></label>
<label>ETA (minutes)<input name="eta_minutes" type="number" min="0" max="600"></label>
<label>Driver<input name="driver"></label>
<button type="submit">Save update</button></form></div>"""
    return page(
        r["id"],
        f"""<div class="card">{banner}<h1>Request {r["id"]}</h1>
<table aria-label="Request details">
<tr><th>Help</th><td>{HELP_TYPES[r["type"]]}</td></tr>
<tr><th>Location</th><td>{html.escape(r["location"])}</td></tr>
<tr><th>Status</th><td data-testid="status">{STATUS_LABEL[r["status"]]}</td></tr>
<tr><th>ETA</th><td data-testid="eta">{eta}</td></tr>
<tr><th>Driver</th><td data-testid="driver">{driver}</td></tr>
</table></div>{_live_tracking_html(r, user)}{update}""",
        user,
    )


# --------------------------------------------------------------------------- RSA-003 dispatcher update


@app.post("/requests/{request_id}/update")
async def update_request(
    request: Request, request_id: str, status: str = Form(...), eta_minutes: str = Form(""), driver: str = Form("")
):
    body: dict = {"status": status}
    if eta_minutes.strip():
        body["eta_minutes"] = int(eta_minutes)
    if driver.strip():
        body["driver"] = driver.strip()
    r = await client.patch(f"/v1/requests/{request_id}", json=body, headers=auth_headers(request))
    if r.status_code == 401:
        return to_signin()
    if r.status_code != 200:
        user = await signed_in(request)
        return page(
            "Update failed",
            f'<div class="card"><p class="error" role="alert">{html.escape(r.json().get("message", ""))}</p>'
            f'<a href="/requests/{request_id}">Back</a></div>',
            user,
        )
    return RedirectResponse(f"/requests/{request_id}", status_code=303)


# --------------------------------------------------------------------------- RSA-004 member cancel


@app.post("/requests/{request_id}/cancel")
async def cancel_request(request: Request, request_id: str):
    r = await client.post(f"/v1/requests/{request_id}/cancel", headers=auth_headers(request))
    if r.status_code == 401:
        return to_signin()
    if r.status_code != 200:
        user = await signed_in(request)
        return page(
            "Cancel failed",
            f'<div class="card"><p class="error" role="alert">{html.escape(r.json().get("message", ""))}</p>'
            f'<a href="/requests/{request_id}">Back</a></div>',
            user,
        )
    return RedirectResponse(f"/requests/{request_id}", status_code=303)


# --------------------------------------------------------------------------- RSA-006 rate my rescue & leaderboard


@app.get("/static/drivers/{filename}")
async def driver_photo(request: Request, filename: str):
    if not await signed_in(request):
        return to_signin()
    if not re.fullmatch(r"[a-z0-9-]+\.jpg", filename):
        return HTMLResponse("Not found", status_code=404)
    path = DRIVERS_STATIC_DIR / filename
    if not path.is_file():
        return HTMLResponse("Not found", status_code=404)
    return FileResponse(path, media_type="image/jpeg")


def _receipt_html(r: dict, rating: dict, avg: float | None = None, thank_you: bool = False) -> str:
    stars = rating["stars"]
    tags_html = "".join(f'<span class="badge" style="margin-right:6px">{html.escape(t)}</span>' for t in rating["tags"])
    if not tags_html:
        tags_html = '<span class="muted">No tags selected</span>'
    comment_text = html.escape(rating["comment"]) if rating.get("comment") else ""
    comment_block = (
        f'<blockquote data-testid="receipt-comment" style="margin:12px 0;padding:10px 14px;'
        f'background:#F8F9FA;border-left:3px solid #0B3D91">{comment_text}</blockquote>'
        if comment_text
        else '<p data-testid="receipt-comment" class="muted"></p>'
    )
    avg_chip = f'<span class="badge" data-testid="driver-updated-avg">★ {avg:.2f} avg</span>' if avg is not None else ""
    heading = "<h1>Thank you!</h1>" if thank_you else f"<h1>Your rating for {html.escape(r['id'])}</h1>"
    return f"""<div class="card">
  {heading}
  <p class="muted">{html.escape(r.get("driver_name") or "Driver")} &bull; {html.escape(r["id"])} {avg_chip}</p>
  <p data-testid="receipt-score"><strong>{stars} out of 5 stars</strong></p>
  <div data-testid="receipt-tags">{tags_html}</div>
  {comment_block}
  <div class="actions">
    <a href="/leaderboard"><button type="button">View Top drivers this month</button></a>
    <a href="/requests/{html.escape(r["id"])}"><button type="button" class="btn-secondary">Back to request</button></a>
  </div>
</div>"""


@app.get("/requests/{request_id}/rate")
async def rate_page(request: Request, request_id: str):
    user = await signed_in(request)
    if not user:
        return to_signin()
    resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
    if resp.status_code != 200:
        return page("Not found", '<div class="card"><h1>Request not found</h1></div>', user)
    r = resp.json()
    if r.get("rating"):
        return page(f"Rating {r['id']}", _receipt_html(r, r["rating"], thank_you=False), user)
    if r["status"] != "completed" or not r.get("driver_name"):
        return page(
            f"Rate {r['id']}",
            f'<div class="card"><h1>Rate your rescue</h1>'
            f'<p class="muted">Ratings open once your rescue is completed.</p>'
            f'<a href="/requests/{html.escape(r["id"])}">'
            f'<button type="button" class="btn-secondary">Back to request</button></a></div>',
            user,
        )

    star_buttons = "".join(
        f'<button type="button" class="star-btn" role="radio" aria-checked="false" '
        f'aria-label="{i} {"star" if i == 1 else "stars"}" data-star="{i}">★ {i}</button>'
        for i in range(1, 6)
    )
    tag_buttons = "".join(
        f'<button type="button" class="tag-btn" aria-pressed="false" '
        f'data-tag="{html.escape(t)}">{html.escape(t)}</button>'
        for t in RATING_TAGS
    )
    driver_name = html.escape(r["driver_name"])
    return page(
        f"Rate {r['id']}",
        f"""<div class="card">
  <h1>How did we do?</h1>
  <p class="muted">Rate your completed rescue {html.escape(r["id"])} with <strong>{driver_name}</strong>.</p>
  <form method="post" action="/requests/{html.escape(r["id"])}/rate" id="rateForm">
    <input type="hidden" name="stars" id="starsInput" value="0">
    <div id="tagsInputs"></div>
    <div class="star-row" role="radiogroup" aria-label="Star rating">{star_buttons}</div>
    <div class="tag-row" role="group" aria-label="Praise tags">{tag_buttons}</div>
    <label>Comment (optional)
      <textarea name="comment" maxlength="300" placeholder="Share what stood out..."></textarea>
    </label>
    <button type="submit">Submit rating</button>
  </form>
</div>
<script>
(() => {{
  const starsInput = document.getElementById("starsInput");
  const starBtns = document.querySelectorAll(".star-btn");
  starBtns.forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const val = Number(btn.dataset.star);
      starsInput.value = String(val);
      starBtns.forEach((b) => {{
        b.setAttribute("aria-checked", Number(b.dataset.star) === val ? "true" : "false");
      }});
    }});
  }});
  const selectedTags = new Set();
  const tagsInputs = document.getElementById("tagsInputs");
  document.querySelectorAll(".tag-btn").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const tag = btn.dataset.tag;
      if (selectedTags.has(tag)) {{
        selectedTags.delete(tag);
        btn.setAttribute("aria-pressed", "false");
      }} else {{
        selectedTags.add(tag);
        btn.setAttribute("aria-pressed", "true");
      }}
      tagsInputs.innerHTML = "";
      selectedTags.forEach((t) => {{
        const inp = document.createElement("input");
        inp.type = "hidden";
        inp.name = "tags";
        inp.value = t;
        tagsInputs.appendChild(inp);
      }});
    }});
  }});
}})();
</script>""",
        user,
    )


@app.post("/requests/{request_id}/rate")
async def submit_rating(
    request: Request,
    request_id: str,
    stars: int = Form(0),
    tags: list[str] = Form(default=[]),
    comment: str = Form(""),
):
    user = await signed_in(request)
    if not user:
        return to_signin()
    r = await client.post(
        f"/v1/requests/{request_id}/rating",
        json={"stars": stars, "tags": tags, "comment": comment or None},
        headers=auth_headers(request),
    )
    if r.status_code == 401:
        return to_signin()
    if r.status_code != 201:
        detail = "; ".join(e["message"] for e in r.json().get("errors", [])) or r.json().get("message", "")
        return page(
            "Rating failed",
            f'<div class="card"><p class="error" role="alert">{html.escape(detail)}</p>'
            f'<a href="/requests/{html.escape(request_id)}/rate">Back</a></div>',
            user,
        )
    req_resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
    req_data = req_resp.json() if req_resp.status_code == 200 else {"id": request_id, "driver_name": "Driver"}
    body = r.json()
    return page(
        "Thank you!",
        _receipt_html(req_data, body["rating"], avg=body["driver_monthly_avg"], thank_you=True),
        user,
    )


@app.get("/leaderboard")
async def leaderboard_page(request: Request, tag: str | None = None):
    user = await signed_in(request)
    if not user:
        return to_signin()
    params = {"tag": tag} if tag else None
    resp = await client.get("/v1/drivers/leaderboard", params=params, headers=auth_headers(request))
    if resp.status_code == 401:
        return to_signin()
    if resp.status_code == 403:
        denied = page(
            "Forbidden", '<div class="card"><p class="error">Only members can view the leaderboard.</p></div>', user
        )
        denied.status_code = 403
        return denied
    if resp.status_code != 200:
        return page("Leaderboard", '<div class="card"><p class="error">Could not load leaderboard.</p></div>', user)

    data = resp.json()
    all_cls = "pill-link active" if not tag else "pill-link"
    filter_links = [f'<a class="{all_cls}" href="/leaderboard">All drivers</a>']
    for t in RATING_TAGS:
        cls = "pill-link active" if tag == t else "pill-link"
        filter_links.append(f'<a class="{cls}" href="/leaderboard?tag={quote(t)}">{html.escape(t)}</a>')

    items_html = []
    for idx, d in enumerate(data["drivers"], start=1):
        name = html.escape(d["driver_name"])
        initials = "".join(part[0] for part in d["driver_name"].split()[:2]).upper()
        avatar = (
            f'<img class="driver-avatar" src="{html.escape(d["photo_url"])}" alt="{name}">'
            if d.get("photo_url")
            else f'<span class="driver-initials" aria-hidden="true">{html.escape(initials)}</span>'
        )
        quote_html = (
            f'<div class="muted">&ldquo;{html.escape(d["latest_quote"])}&rdquo;</div>' if d.get("latest_quote") else ""
        )
        tags_summary = " &bull; ".join(f"{html.escape(k)} ({v})" for k, v in d.get("tag_counts", {}).items() if v > 0)
        items_html.append(
            f'<li class="standing-item">'
            f'<div class="standing-left"><strong>#{idx}</strong>{avatar}'
            f"<div><div><strong>{name}</strong></div>"
            f'<div class="muted">{html.escape(d.get("truck") or "")}</div>'
            f'<div class="muted">{tags_summary}</div>{quote_html}</div></div>'
            f'<div class="standing-right"><div><strong>★ {d["avg_stars"]:.2f}</strong></div>'
            f'<div class="muted">{d["rating_count"]} ratings</div></div></li>'
        )

    standings = (
        f'<ol data-testid="standings-list" style="list-style:none;padding:0;margin:0">{"".join(items_html)}</ol>'
        if items_html
        else '<p class="muted" data-testid="standings-list">No drivers match this filter yet.</p>'
    )
    return page(
        "Top drivers this month",
        f"""<div class="card">
  <h1>Top drivers this month</h1>
  <p class="muted">
    {html.escape(data["month"])} &bull; Fleet average ★ {data["fleet_avg_stars"]:.2f} &bull;
    {data["total_ratings"]} ratings
  </p>
  <div class="tag-row" role="group" aria-label="Filter drivers by tag">{"".join(filter_links)}</div>
  {standings}
</div>""",
        user,
    )
