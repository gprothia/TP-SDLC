#!/usr/bin/env bash
# The demo's production space on GKE and its canary releases (standards/release.md REL-3, REL-4).
# The release workflow (.github/workflows/release.yml) runs these; people and agents use
# them to look and to tidy up.
#
#   scripts/prod.sh up [tag]          create the space: 9 stable copies of the API at <tag> (default: main)
#   scripts/prod.sh canary <tag>      start 1 canary copy of <tag> next to the 9 stable ones (about 10%)
#   scripts/prod.sh measure [secs]    run synthetic member traffic, write reports/prod/load.json
#   scripts/prod.sh promote <tag>     make <tag> the stable version and remove the canary
#   scripts/prod.sh rollback          remove the canary; everyone is back on stable
#   scripts/prod.sh logs              save the canary's logs to reports/prod/canary.log
#   scripts/prod.sh status            what is running: copies per track and version
#   scripts/prod.sh down              delete the space (do this after a demo)
#
# Images come from Artifact Registry, tagged with the commit (built by the UAT deploy for
# main, by PR checks for PRs). Settings: deploy/sandbox/sandbox.env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f deploy/sandbox/sandbox.env ]]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    [[ -z "${!key:-}" ]] && export "$key=$value"
  done < deploy/sandbox/sandbox.env
fi
REPO_SLUG="$(basename "$(git remote get-url origin 2>/dev/null || pwd)" .git | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-')"
export REPO_SLUG
export NS="${PROD_NS:-${REPO_SLUG}-prod}"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/api"
REPORTS="reports/prod"

render() { python3 -c 'import os,sys; sys.stdout.write(os.path.expandvars(sys.stdin.read()))'; }
log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

credentials() {
  # In GitHub Actions, get-gke-credentials has already set up kubectl.
  [[ -n "${GITHUB_ACTIONS:-}" ]] && return 0
  export CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS=false
  gcloud container clusters get-credentials "$CLUSTER" --region "$REGION" --project "$PROJECT_ID" >/dev/null
}

exists() { kubectl get namespace "$NS" >/dev/null 2>&1; }
short() { echo "${1:0:7}"; }
current_stable() { kubectl -n "$NS" get deploy api-stable -o jsonpath='{.spec.template.spec.containers[0].image}' | sed 's/.*://'; }

up() {
  credentials
  local tag="${1:-}"
  if [[ -z "$tag" ]]; then git fetch -q origin main; tag="$(git rev-parse origin/main)"; fi
  log "Creating production space $NS: 9 stable copies of $(short "$tag")"
  render < deploy/prod/namespace.yaml | kubectl apply -f -
  STABLE_TAG="$tag" render < deploy/prod/api.yaml | kubectl apply -f -
  kubectl -n "$NS" rollout status deploy/api-stable --timeout=10m
}

canary() {
  credentials
  local tag="${1:?usage: prod.sh canary <tag>}"
  exists || up "$tag"
  log "Canary: 1 copy of $(short "$tag") next to 9 stable copies of $(short "$(current_stable)")"
  kubectl -n "$NS" set image deploy/api-canary api="$IMAGE:$tag"
  kubectl -n "$NS" set env deploy/api-canary APP_VERSION="$tag"
  kubectl -n "$NS" scale deploy/api-canary --replicas=1
  kubectl -n "$NS" rollout status deploy/api-canary --timeout=10m
}

measure() {
  credentials
  local secs="${1:-180}" image
  image="$(kubectl -n "$NS" get deploy api-canary -o jsonpath='{.spec.template.spec.containers[0].image}')"
  mkdir -p "$REPORTS"
  log "Synthetic member traffic for ${secs}s (results per track: stable / canary)"
  kubectl -n "$NS" delete pod loadgen --ignore-not-found --wait=true >/dev/null
  kubectl -n "$NS" create configmap loadgen --from-file=tools/loadgen.py --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl -n "$NS" apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata: { name: loadgen, labels: { app: loadgen } }
spec:
  restartPolicy: Never
  containers:
    - name: loadgen
      image: $image
      command: ["python", "/tools/loadgen.py"]
      env:
        - { name: API_BASE_URL, value: "http://api:8080" }
        - { name: DURATION_S, value: "$secs" }
      resources: { requests: { cpu: 500m, memory: 256Mi } }
      volumeMounts: [{ name: tools, mountPath: /tools }]
  volumes: [{ name: tools, configMap: { name: loadgen } }]
EOF
  kubectl -n "$NS" wait pod/loadgen --for=jsonpath='{.status.phase}'=Running --timeout=10m >/dev/null || true
  kubectl -n "$NS" logs -f pod/loadgen | tee "$REPORTS/loadgen.log" | grep -v '^LOADGEN_RESULT'
  grep '^LOADGEN_RESULT ' "$REPORTS/loadgen.log" | tail -1 | cut -d' ' -f2- > "$REPORTS/load.json"
  [[ -s "$REPORTS/load.json" ]] || { echo "error: no load result (see $REPORTS/loadgen.log)" >&2; exit 3; }
  echo "Result: $REPORTS/load.json"
}

promote() {
  credentials
  local tag="${1:?usage: prod.sh promote <tag>}"
  log "Promote: all 9 stable copies to $(short "$tag"), canary removed"
  kubectl -n "$NS" set image deploy/api-stable api="$IMAGE:$tag"
  kubectl -n "$NS" set env deploy/api-stable APP_VERSION="$tag"
  kubectl -n "$NS" rollout status deploy/api-stable --timeout=10m
  kubectl -n "$NS" scale deploy/api-canary --replicas=0
}

rollback() {
  credentials
  log "Rollback: canary removed; all traffic on stable $(short "$(current_stable)")"
  kubectl -n "$NS" scale deploy/api-canary --replicas=0
}

logs() {
  credentials
  mkdir -p "$REPORTS"
  kubectl -n "$NS" logs -l track=canary --tail=400 --prefix > "$REPORTS/canary.log" 2>/dev/null || true
  echo "Canary logs: $REPORTS/canary.log ($(wc -l < "$REPORTS/canary.log") lines)"
}

status() {
  credentials
  exists || { echo "Production space $NS does not exist (scripts/prod.sh up)"; return 0; }
  echo "Production space: $NS on cluster $CLUSTER ($REGION)"
  for track in stable canary; do
    local img ready
    img="$(kubectl -n "$NS" get deploy "api-$track" -o jsonpath='{.spec.template.spec.containers[0].image}')"
    ready="$(kubectl -n "$NS" get deploy "api-$track" -o jsonpath='{.status.readyReplicas}')"
    printf '  %-7s %s copies ready   version %s\n' "$track" "${ready:-0}" "$(short "${img##*:}")"
  done
  kubectl -n "$NS" get pods -L track -o wide
}

down() {
  credentials
  log "Deleting production space $NS"
  kubectl delete namespace "$NS" --ignore-not-found --wait=false
}

case "${1:-}" in
  up) up "${2:-}" ;;
  canary) canary "${2:-}" ;;
  measure) measure "${2:-180}" ;;
  promote) promote "${2:-}" ;;
  rollback) rollback ;;
  logs) logs ;;
  status) status ;;
  down) down ;;
  *) sed -n '2,17p' "$0"; exit 1 ;;
esac
