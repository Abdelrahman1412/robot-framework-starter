#!/usr/bin/env bash
# Start the Acme HR demo app (unless one is already serving), run the suite in parallel with pabot,
# then merge everything into one report with rebot. Extra args go to pabot, e.g.:
#   scripts/run.sh --include smoke
#   RERUN_FAILED=true scripts/run.sh --exclude db
set -uo pipefail

cd "$(dirname "$0")/.."
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

RUN=${RUN:-uv run}
PROCESSES=${PROCESSES:-2}
RERUN_FAILED=${RERUN_FAILED:-false}
export ACME_ENV=${ACME_ENV:-local}
BASE_URL=$($RUN python -c "from variables.config import get_variables as g; print(g()['BASE_URL'])")
START_APP=$($RUN python -c "from variables.config import get_variables as g; print(g()['START_APP'])")

rm -rf results
mkdir -p results

healthy() { curl -fsS "$BASE_URL/api/health" >/dev/null 2>&1; }

APP_PID=""
if [[ "$START_APP" == "True" ]] && ! healthy; then
  ACME_PORT=$($RUN python -c "from urllib.parse import urlparse; print(urlparse('$BASE_URL').port or 80)") \
  ACME_DB_PATH=${ACME_DB_PATH:-results/acme_hr.sqlite3} \
    $RUN python -m demo_app.acme_hr >results/acme_hr.log 2>&1 &
  APP_PID=$!
  trap '[[ -n "$APP_PID" ]] && kill "$APP_PID" 2>/dev/null' EXIT
  for _ in $(seq 1 40); do healthy && break; sleep 0.25; done
  healthy || { echo "Acme HR did not start, see results/acme_hr.log" >&2; exit 2; }
  echo "Acme HR started at $BASE_URL (pid $APP_PID)"
fi

$RUN pabot --processes "$PROCESSES" --outputdir results/pabot "$@" tests
status=$?

outputs=(results/pabot/output.xml)
if [[ $status -ne 0 && "$RERUN_FAILED" == "true" ]]; then
  echo "Re-running failed tests once to separate flaky from broken..."
  $RUN robot --rerunfailed results/pabot/output.xml --outputdir results/rerun --output rerun.xml \
    --log NONE --report NONE "$@" tests
  outputs+=(results/rerun/rerun.xml)
fi

# rebot merges the parallel (and optional rerun) outputs into one log.html / report.html / xunit.xml.
$RUN rebot --name "Acme HR" --merge --outputdir results --output output.xml --xunit xunit.xml "${outputs[@]}"
exit $?
