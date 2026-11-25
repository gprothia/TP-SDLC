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
import time

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

API_URL = os.environ.get("API_URL", "http://localhost:8080")
API_AUDIENCE = os.environ.get("API_AUDIENCE", "")
COOKIE = "session"
# Secure cookies everywhere served over HTTPS (SEC-9). Only in-cluster sandboxes, which use
# plain HTTP, turn it off (deploy/app/web.yaml).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
# Sent on every page (SEC-8): no MIME sniffing, no framing, no referrer leaks, HTTPS only.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=31536000",
}


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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


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
            '<a href="/leaderboard">Top drivers</a>'
        )
    elif user:
        nav = '<a href="/requests">All requests</a><a href="/leaderboard">Top drivers</a>'
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
    resp.set_cookie(COOKIE, r.json()["token"], httponly=True, samesite="lax", secure=COOKIE_SECURE)
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
    rate_cta = ""
    if user["role"] == "member" and r["status"] == "completed" and not r.get("rating"):
        rate_cta = (
            f'<div class="card"><a href="/requests/{r["id"]}/rate"><button type="button">Rate rescue</button></a></div>'
        )
    return page(
        r["id"],
        f"""<div class="card">{banner}<h1>Request {r["id"]}</h1>
<table aria-label="Request details">
<tr><th>Help</th><td>{HELP_TYPES[r["type"]]}</td></tr>
<tr><th>Location</th><td>{html.escape(r["location"])}</td></tr>
<tr><th>Status</th><td data-testid="status">{STATUS_LABEL[r["status"]]}</td></tr>
<tr><th>ETA</th><td data-testid="eta">{eta}</td></tr>
<tr><th>Driver</th><td data-testid="driver">{driver}</td></tr>
</table></div>{rate_cta}{_live_tracking_html(r, user)}{update}""",
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


# --------------------------------------------------------------------------- RSA-006 rate my rescue

RATING_TAGS = ("On time", "Friendly driver", "Explained the fix")
AVATAR_COLORS = {
    "sam": ("#0B3D91", "#DBEAFE"),
    "maria": ("#137333", "#D1FAE5"),
    "elena": ("#B45309", "#FEF3C7"),
    "marcus": ("#374151", "#E5E7EB"),
    "devon": ("#9D174D", "#FCE7F3"),
}


@app.get("/avatars/{slug}.svg")
async def driver_avatar(slug: str):
    fg, bg = AVATAR_COLORS.get(slug.lower(), ("#0B3D91", "#E8F0FE"))
    initial = html.escape(slug[:1].upper() if slug else "D")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
        f'<circle cx="32" cy="32" r="32" fill="{bg}"/>'
        f'<text x="32" y="40" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="26" font-weight="700" fill="{fg}">{initial}</text></svg>'
    )
    return HTMLResponse(content=svg, media_type="image/svg+xml")


def _rate_form_html(request_id: str, r: dict, error: str = "") -> str:
    err_html = f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ""
    d_name = html.escape(r.get("driver_name") or r.get("driver") or "Your driver")
    stars_html = "".join(
        f'<label style="display:inline-flex;flex-direction:row;align-items:center;gap:6px;margin-right:12px">'
        f'<input type="radio" name="stars" value="{n}"> {n} {"star" if n == 1 else "stars"}</label>'
        for n in range(1, 6)
    )
    tags_html = "".join(
        f'<label style="display:inline-flex;flex-direction:row;align-items:center;gap:6px;margin-right:12px">'
        f'<input type="checkbox" name="tags" value="{html.escape(tag)}"> {html.escape(tag)}</label>'
        for tag in RATING_TAGS
    )
    return f"""<div class="card">
<h1>How did we do?</h1>
<p class="muted">Request {html.escape(request_id)} &bull; Driver: {d_name}</p>
{err_html}
<form method="post" action="/requests/{html.escape(request_id)}/rate">
  <fieldset style="border:0;padding:0;margin:0 0 14px">
    <legend style="font-size:14px;margin-bottom:6px">Your rating</legend>{stars_html}
  </fieldset>
  <fieldset style="border:0;padding:0;margin:0 0 14px">
    <legend style="font-size:14px;margin-bottom:6px">What went well?</legend>{tags_html}
  </fieldset>
  <label for="comment">Leave a comment (optional)
    <textarea id="comment" name="comment" rows="3" maxlength="300"
      style="padding:9px;border:1px solid #DADCE0;border-radius:8px;font-size:15px"></textarea>
  </label>
  <button type="submit">Submit rating</button>
</form></div>"""


@app.get("/requests/{request_id}/rate")
async def rate_form(request: Request, request_id: str):
    user = await signed_in(request)
    if not user:
        return to_signin()
    resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
    if resp.status_code != 200:
        return page("Not found", '<div class="card"><h1>Request not found</h1></div>', user)
    return page(f"Rate {request_id}", _rate_form_html(request_id, resp.json()), user)


@app.post("/requests/{request_id}/rate")
async def submit_rating(request: Request, request_id: str):
    user = await signed_in(request)
    if not user:
        return to_signin()
    form = await request.form()
    stars_raw = str(form.get("stars", "")).strip()
    tags = [str(t) for t in form.getlist("tags")]
    comment = str(form.get("comment", ""))
    if not stars_raw.isdigit():
        req_resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
        req_data = req_resp.json() if req_resp.status_code == 200 else {}
        return page(f"Rate {request_id}", _rate_form_html(request_id, req_data, "Please select 1 to 5 stars."), user)

    r = await client.post(
        f"/v1/requests/{request_id}/rating",
        json={"stars": int(stars_raw), "tags": tags, "comment": comment},
        headers=auth_headers(request),
    )
    if r.status_code == 401:
        return to_signin()
    if r.status_code != 201:
        req_resp = await client.get(f"/v1/requests/{request_id}", headers=auth_headers(request))
        req_data = req_resp.json() if req_resp.status_code == 200 else {}
        return page(
            f"Rate {request_id}",
            _rate_form_html(request_id, req_data, r.json().get("message", "Could not submit rating.")),
            user,
        )

    rating = r.json()
    board_resp = await client.get("/v1/drivers/leaderboard", headers=auth_headers(request))
    avg_text = "Updated"
    if board_resp.status_code == 200:
        for d in board_resp.json().get("drivers", []):
            if d["driver_name"] == rating["driver_name"] or d["driver_name"].split(" ")[0] == rating["driver_name"]:
                avg_text = f"{d['average_stars']} ★ ({d['rating_count']} ratings)"
                break
    tags_out = ", ".join(html.escape(t) for t in rating.get("tags", [])) or "None"
    comment_out = html.escape(rating["comment"]) if rating.get("comment") else "No comment left"
    return page(
        "Thanks for your feedback!",
        f"""<div class="card">
<h1>Thanks for your feedback!</h1>
<p>Your rating for <strong>{html.escape(rating["driver_name"])}</strong>
  on {html.escape(request_id)} has been recorded.</p>
<p data-testid="submitted-stars">Rating: <strong>{rating["stars"]} / 5 ★</strong></p>
<p data-testid="submitted-tags">Tags: {tags_out}</p>
<p data-testid="submitted-comment">Comment: {comment_out}</p>
<p data-testid="driver-average">Driver monthly average: <strong>{html.escape(avg_text)}</strong></p>
<div class="actions">
  <a href="/leaderboard"><button type="button">View top drivers this month</button></a>
  <a href="/requests"><button type="button" class="btn-secondary">Back to my requests</button></a>
</div></div>""",
        user,
    )


@app.get("/leaderboard")
async def leaderboard_page(request: Request):
    user = await signed_in(request)
    if not user:
        return to_signin()
    resp = await client.get("/v1/drivers/leaderboard", headers=auth_headers(request))
    if resp.status_code == 401:
        return to_signin()
    drivers = resp.json().get("drivers", []) if resp.status_code == 200 else []
    rows = "".join(
        f"""<div class="card" style="display:flex;align-items:center;justify-content:space-between;gap:14px">
  <div style="display:flex;align-items:center;gap:12px">
    <strong>#{idx}</strong>
    <img src="{html.escape(d["photo_url"])}" alt="{html.escape(d["driver_name"])}"
      width="48" height="48" style="border-radius:50%">
    <div>
      <div><strong>{html.escape(d["driver_name"])}</strong></div>
      <div class="muted">{html.escape(d["truck_unit"])} &bull; {d["rescue_count"]} rescues this month</div>
    </div>
  </div>
  <div style="text-align:right">
    <div><strong>★ {d["average_stars"]}</strong></div>
    <div class="muted">{d["rating_count"]} ratings</div>
  </div>
</div>"""
        for idx, d in enumerate(drivers, start=1)
    )
    return page(
        "Top drivers this month",
        f"""<div class="card"><h1>Top drivers this month</h1>
<p class="muted">Highest-rated roadside technicians based on member feedback (5+ ratings).</p></div>
<div data-testid="leaderboard-list">{rows}</div>""",
        user,
    )
