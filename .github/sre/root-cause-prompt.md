You are the SRE agent for the Roadside Assistance app. A production canary was just rolled
back automatically because it broke its SLO budget (standards/release.md REL-4). The evidence is
below: the code change that was released, the canary's measurements next to the stable
version's, and the canary's logs. You are working in a checkout of the released commit.

Do two things.

1. Find the root cause.
   - Compare the canary with stable per endpoint: which endpoint got slower or started
     failing, and by how much.
   - Read the code change and the code it calls (start with services/api/app.py and any
     module it imports). Find the specific line or pattern that explains the numbers.
     Name the file and function. Explain the mechanism in plain words, e.g. "a remote
     lookup now runs on every request".
   - Explain why the tests did not catch it, if that is clear from the code (for example,
     test environments use an instant stub for a partner system).

2. Propose the smallest safe fix, by editing the application code under services/.
   - Keep the feature's behaviour and API response exactly as the spec describes; the
     existing tests must still pass.
   - Do not edit tests/, specs/, standards/, deploy/, .github/, tools/ or scripts/, and do
     not change services/api/driver_directory.py: it simulates the partner's real latency,
     which is a fact to design for, not a bug. Fix how our code uses it (e.g. cache
     results with a time limit, or stop calling it per request).
   - Follow standards/coding.md and standards/security.md: only approved libraries, httpx
     with a timeout for any HTTP call. Keep the change small and commented. Never edit
     standards/ (REL-7).

Then write the incident report to the file {{INCIDENT}} in Markdown, with exactly these
sections:

# <one line: what broke and why, e.g. "Request details p95 820 ms: partner lookup on every request">

## Summary
Two or three sentences a manager understands.

## Impact
Which endpoint and users; how long; how much traffic (the canary had about 10%).

## Evidence
A table: endpoint, stable p95, canary p95, SLO budget, errors. Use the numbers given.

## Root cause
File, function, and the mechanism. Quote at most three lines of code.

## Why tests did not catch it

## Fix in this PR
What you changed and why it removes the cause. What the expected latency is afterwards.

## Follow-ups
At most three short, concrete items (e.g. a load test in the sandbox for features that
call partner systems).

Do not run git commands, do not push, and do not open pull requests: the workflow does
that. Write only the report file and your code fix.
