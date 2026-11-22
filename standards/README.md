# Engineering standards

Every feature follows these. Agents read them through `AGENTS.md`; every spec answers them in
its enterprise sections (`specs/_TEMPLATE.md`); `scripts/check_spec.py` rejects a spec that
skips one; tests prove them (`specs/STD-001-enterprise-baseline.md` for the shared rules).

| Standard | File | Owner (CODEOWNERS) |
|---|---|---|
| Authentication, Authorization, Accounting | [aaa.md](aaa.md) | Security |
| API design | [api.md](api.md) | Architecture |
| Logging | [logging.md](logging.md) | SRE |
| Service levels and releases | [slo.md](slo.md) | SRE |
| Code style | [code-style.md](code-style.md) | Engineering |
| Security basics | [security.md](security.md) | Security |

In a real organisation this folder is a shared repository used by every team; this demo keeps
a copy here so it can be shown in one place.
