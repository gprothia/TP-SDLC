#!/usr/bin/env bash
# Pre-PR GKE sandbox: build this commit's images with Cloud Build, stage the app as pods in the
# branch's own namespace, run ALL tests (new + regression) in a test pod, fetch the reports,
# and publish the result to GitHub for the exact commit.
#
#   scripts/sandbox.sh all      build + up + test   (what /build-spec runs)
#   scripts/sandbox.sh build    build and push api, web and tests images (Cloud Build, no local Docker)
#   scripts/sandbox.sh up       create/refresh the namespace and deploy the app
#   scripts/sandbox.sh test     run the test-runner pod, fetch reports, write the result
#   scripts/sandbox.sh load     load test with the partner's production latency, judged against the SLO
#   scripts/sandbox.sh publish  post the last result (+ load test) as a commit status + PR comment (after push)
#   scripts/sandbox.sh down     delete the namespace
#   scripts/sandbox.sh status   show what's running
#
# Needs: gcloud (`gcloud auth login`), kubectl, python3, git; gh (`gh auth login`) for publish.
# Settings: deploy/sandbox/sandbox.env (PROJECT_ID, REGION, CLUSTER, AR_REPO).
# Commit first: images are tagged with the commit so the evidence matches what the PR contains.
# SANDBOX_ALLOW_DIRTY=1 allows a quick run on uncommitted changes; such results can't be published.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# --- settings ---------------------------------------------------------------
if [[ -f deploy/sandbox/sandbox.env ]]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    [[ -z "${!key:-}" ]] && export "$key=$value"
  done < deploy/sandbox/sandbox.env
fi
for v in PROJECT_ID REGION CLUSTER AR_REPO; do
  if [[ -z "${!v:-}" || "${!v}" == your-* ]]; then
    echo "error: set $v in deploy/sandbox/sandbox.env (see README: Google Cloud setup)" >&2; exit 2
  fi
done
AR="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
SLUG="$(echo "$BRANCH" | tr '[:upper:]' '[:lower:]' | sed -E 's#[^a-z0-9]+#-#g; s#^-+|-+$##g' | cut -c1-40)"
REPO_SLUG="$(basename "$(git remote get-url origin 2>/dev/null || pwd)" .git | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-')"
export REPO_SLUG
export NS="${SANDBOX_NS:-dev-${REPO_SLUG}-${SLUG}}"
NS="${NS:0:63}"; NS="${NS%-}"
SHA_FULL="$(git rev-parse HEAD)"
TAG="dev-$(git rev-parse --short HEAD)"
DIRTY="$(git status --porcelain -- services tests deploy/app deploy/sandbox/namespace.yaml deploy/sandbox/test-runner.yaml)"
TAG_FILE="deploy/overlay-dev/.tag"
REPORTS="reports/${NS}"

render() { python3 -c 'import os,sys; sys.stdout.write(os.path.expandvars(sys.stdin.read()))'; }
log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

credentials() {
  # Authenticate kubectl with the same account as `gcloud auth login` (see "Needs" above).
  # Without this, a gcloud config with container/use_application_default_credentials=true
  # makes gke-gcloud-auth-plugin look for application default credentials instead.
  export CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS=false
  gcloud container clusters get-credentials "$CLUSTER" --region "$REGION" --project "$PROJECT_ID" >/dev/null
}

# --- steps -----------------------------------------------------------------
build() {
  if [[ -n "$DIRTY" ]]; then
    if [[ "${SANDBOX_ALLOW_DIRTY:-}" != "1" ]]; then
      echo "error: uncommitted changes in services/, tests/ or deploy/ - commit first, so the" >&2
      echo "       sandbox result matches a commit (or SANDBOX_ALLOW_DIRTY=1 for an unpublishable run)" >&2
      exit 4
    fi
    TAG="${TAG}-wip$(date +%s)"   # never reuse an image tag for uncommitted code
  fi
  log "Building images with Cloud Build (tag $TAG)"
  for svc in api web; do
    gcloud builds submit "services/$svc" --tag "$AR/$svc:$TAG" --project "$PROJECT_ID" --region "$REGION" --quiet
  done
  gcloud builds submit tests --tag "$AR/tests:$TAG" --project "$PROJECT_ID" --region "$REGION" --quiet
  mkdir -p deploy/overlay-dev && echo "$TAG" > "$TAG_FILE"
}

current_tag() {
  [[ -f "$TAG_FILE" ]] || { echo "error: no images built yet - run: scripts/sandbox.sh build" >&2; exit 3; }
  cat "$TAG_FILE"
}

up() {
  local tag; tag="$(current_tag)"
  credentials
  log "Staging $BRANCH ($tag) as pods in namespace $NS"
  SANDBOX_KIND=dev PR_NUMBER=none SHA="$tag" CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    render < deploy/sandbox/namespace.yaml | kubectl apply -f -
  cat > deploy/overlay-dev/kustomization.yaml <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ${NS}
resources: ["../app"]
images:
  - { name: api, newName: ${AR}/api, newTag: "${tag}" }
  - { name: web, newName: ${AR}/web, newTag: "${tag}" }
EOF
  kubectl apply -k deploy/overlay-dev
  echo "Waiting for the app (Autopilot may need a few minutes to add capacity)..."
  kubectl -n "$NS" rollout status deploy/api --timeout=10m
  kubectl -n "$NS" rollout status deploy/web --timeout=10m
}

test_run() {
  local tag code=""; tag="$(current_tag)"
  credentials
  log "Running ALL tests (new + regression) inside $NS"
  kubectl -n "$NS" delete pod test-runner --ignore-not-found --wait=true
  TEST_IMAGE="$AR/tests:$tag" render < deploy/sandbox/test-runner.yaml | kubectl apply -f -
  # Wait for the pod to start (not "Ready": the tests container exits when it's done).
  kubectl -n "$NS" wait pod/test-runner --for=jsonpath='{.status.phase}'=Running --timeout=10m || true
  kubectl -n "$NS" logs -f pod/test-runner -c tests || true
  for _ in $(seq 1 60); do
    code="$(kubectl -n "$NS" get pod test-runner \
      -o jsonpath='{.status.containerStatuses[?(@.name=="tests")].state.terminated.exitCode}')"
    [[ -n "$code" ]] && break; sleep 5
  done
  rm -rf "$REPORTS" && mkdir -p "$REPORTS"
  kubectl -n "$NS" cp test-runner:/reports "$REPORTS" -c results >/dev/null 2>&1 || echo "warning: could not copy reports"
  python3 scripts/sandbox_report.py "$REPORTS" "$NS" "$tag" "${code:-1}" "$SHA_FULL" "$BRANCH"
  [[ "${code:-1}" == "0" ]]
}

load_test() {
  # Production-like load in this sandbox: the partner's real latency (as in deploy/prod) and
  # synthetic member traffic (tools/loadgen.py), judged like a canary (scripts/check_slo.py).
  local tag secs="${1:-120}" slo p95 err specs rc=0
  tag="$(current_tag)"
  credentials
  log "Load test in $NS: partner latency as in production, ${secs}s of member traffic"
  kubectl -n "$NS" set env deploy/api PARTNER_LATENCY_MS=600 APP_TRACK=canary >/dev/null
  kubectl -n "$NS" rollout status deploy/api --timeout=5m
  kubectl -n "$NS" delete pod loadgen --ignore-not-found --wait=true >/dev/null
  kubectl -n "$NS" create configmap loadgen --from-file=tools/loadgen.py --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  sed -e "s#__IMAGE__#$AR/api:$tag#" -e "s#__SECS__#$secs#" <<'POD' | kubectl -n "$NS" apply -f -
apiVersion: v1
kind: Pod
metadata: { name: loadgen }
spec:
  restartPolicy: Never
  containers:
    - name: loadgen
      image: __IMAGE__
      command: ["python", "/tools/loadgen.py"]
      env:
        - { name: API_BASE_URL, value: "http://api:8080" }
        - { name: DURATION_S, value: "__SECS__" }
      resources: { requests: { cpu: 500m, memory: 256Mi } }
      volumeMounts: [{ name: tools, mountPath: /tools }]
  volumes: [{ name: tools, configMap: { name: loadgen } }]
POD
  kubectl -n "$NS" wait pod/loadgen --for=jsonpath='{.status.phase}'=Running --timeout=10m >/dev/null || true
  mkdir -p "$REPORTS"
  kubectl -n "$NS" logs -f pod/loadgen | tee "$REPORTS/loadgen.log" | grep -v '^LOADGEN_RESULT' || true
  grep '^LOADGEN_RESULT ' "$REPORTS/loadgen.log" | tail -1 | cut -d' ' -f2- > "$REPORTS/load.json"
  kubectl -n "$NS" set env deploy/api PARTNER_LATENCY_MS- APP_TRACK- >/dev/null   # back to the test stub
  [[ -s "$REPORTS/load.json" ]] || { echo "error: no load result (see $REPORTS/loadgen.log)" >&2; return 3; }

  git fetch -q origin main || true
  specs="$(git diff --name-only origin/main...HEAD -- 'specs/*.md' 2>/dev/null || true)"
  # shellcheck disable=SC2086  # word splitting wanted: one argument per spec file
  slo="$(python3 scripts/check_slo.py target $specs)"
  p95="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["p95_latency_ms"])' "$slo")"
  err="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["error_rate_pct"])' "$slo")"
  python3 scripts/check_slo.py judge "$REPORTS/load.json" --p95 "$p95" --err "$err" \
    --md "$REPORTS/load-judge.md" >/dev/null || rc=$?
  {
    echo "### GKE load test (pre-PR): $([[ $rc == 0 ]] && echo PASSED || echo FAILED)"
    echo
    echo "Partner latency as in production, ${secs}s of synthetic member traffic, commit \`${SHA_FULL:0:7}\`, namespace \`$NS\`."
    echo
    cat "$REPORTS/load-judge.md"
  } > "$REPORTS/load.md"
  echo "$SHA_FULL" > "$REPORTS/load.commit"
  cat "$REPORTS/load-judge.md"
  log "Load test: $([[ $rc == 0 ]] && echo PASSED || echo FAILED) (budget p95 ${p95} ms, errors ${err}%)"
  return "$rc"
}

publish() {
  local result="$REPORTS/result.json" repo status passed total images commit pr desc state
  [[ -f "$result" ]] || { echo "error: no sandbox result for $NS - run: scripts/sandbox.sh all" >&2; exit 5; }
  read -r status passed total images commit < <(python3 -c '
import json, sys
r = json.load(open(sys.argv[1]))
print(r["status"], r["passed"], r["total"], r["images"], r["commit"])' "$result")
  if [[ "$images" == *-wip* ]]; then
    echo "error: that run used uncommitted changes ($images) - commit, then scripts/sandbox.sh all" >&2; exit 6
  fi
  if [[ "$commit" != "$SHA_FULL" ]]; then
    echo "error: the last sandbox run tested ${commit:0:7}, but HEAD is ${SHA_FULL:0:7} - run scripts/sandbox.sh all again" >&2; exit 7
  fi
  repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
  if ! gh api "repos/$repo/commits/$SHA_FULL" --silent 2>/dev/null; then
    echo "error: commit ${SHA_FULL:0:7} isn't on GitHub yet - run: git push -u origin HEAD" >&2; exit 8
  fi
  if [[ "$status" == "PASSED" ]]; then state=success; else state=failure; fi
  desc="$passed/$total tests passed on GKE ($NS, images $images)"
  log "Commit status on ${SHA_FULL:0:7}: $state - $desc"
  gh api "repos/$repo/statuses/$SHA_FULL" -f state="$state" -f context="GKE sandbox (pre-PR)" \
    -f description="${desc:0:140}" --silent

  pr="$(gh pr view --json number -q .number 2>/dev/null || true)"
  if [[ -z "$pr" ]]; then
    echo "No PR for $BRANCH yet: status posted. Run publish again after gh pr create to add the comment."
    return 0
  fi
  local marker="<!-- gke-sandbox-evidence -->" body existing
  body="$marker"$'\n'"$(cat "$REPORTS/summary.md")"
  if [[ -f "$REPORTS/load.md" && "$(cat "$REPORTS/load.commit" 2>/dev/null)" == "$SHA_FULL" ]]; then
    body+=$'\n\n'"$(cat "$REPORTS/load.md")"
  fi
  existing="$(gh api "repos/$repo/issues/$pr/comments" --paginate \
    --jq ".[] | select(.body | startswith(\"$marker\")) | .id" | tail -1)"
  if [[ -n "$existing" ]]; then
    gh api -X PATCH "repos/$repo/issues/comments/$existing" -f body="$body" --silent
    log "Updated the evidence comment on PR #$pr"
  else
    gh api "repos/$repo/issues/$pr/comments" -f body="$body" --silent
    log "Posted the evidence comment on PR #$pr"
  fi
}

down() {
  credentials
  log "Deleting namespace $NS"
  kubectl delete namespace "$NS" --ignore-not-found --wait=false
}

status() {
  credentials
  kubectl -n "$NS" get pods,svc 2>/dev/null || echo "namespace $NS does not exist"
}

case "${1:-}" in
  build) build ;;
  up) up ;;
  test) test_run ;;
  load) load_test "${2:-120}" ;;
  publish) publish ;;
  down) down ;;
  status) status ;;
  all) build; up; test_run ;;
  *) sed -n '2,18p' "$0"; exit 1 ;;
esac
