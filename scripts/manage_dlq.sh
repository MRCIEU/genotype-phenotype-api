#!/bin/bash
#
# Manage the GWAS dead letter queue and internal API endpoints.
#
# Usage:
#   ./manage_dlq.sh list
#   ./manage_dlq.sh retry <guid>
#   ./manage_dlq.sh retry-all
#   ./manage_dlq.sh rerun <guid>
#   ./manage_dlq.sh delete-all
#   ./manage_dlq.sh delete <guid>
#
# Options:
#   --api-url URL    API base URL (default: http://127.0.0.1:8000 or GPMAP_API_URL)
#
set -e

API_URL="${GPMAP_API_URL:-http://127.0.0.1:8000}"
API_URL="${API_URL%/}"
BASE="${API_URL}/v1/internal"

usage() {
    local code="${1:-0}"
    echo "Manage the GWAS dead letter queue and internal API endpoints."
    echo ""
    echo "Usage:"
    echo "  $0 list"
    echo "  $0 retry <guid>"
    echo "  $0 retry-all"
    echo "  $0 rerun <guid>"
    echo "  $0 delete-all"
    echo "  $0 delete <guid>"
    echo ""
    echo "Options:"
    echo "  --api-url URL    API base URL (default: http://127.0.0.1:8000 or GPMAP_API_URL)"
    exit "$code"
}

# Parse options
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--api-url" ]]; then
        API_URL="$2"
        API_URL="${API_URL%/}"
        BASE="${API_URL}/v1/internal"
        shift 2
    elif [[ "$1" == "--help" || "$1" == "-h" ]]; then
        usage
    else
        break
    fi
done

CMD="${1:-}"
shift || true

if [[ -z "$CMD" ]]; then
    echo "Error: command required" >&2
    usage 1
fi

if [[ "$CMD" == "list" ]]; then
    curl -sS "${BASE}/gwas-dlq" | jq .entries
elif [[ "$CMD" == "retry" ]]; then
    GUID="${1:?Error: GUID required for retry}"
    curl -sS -X POST "${BASE}/gwas-dlq/${GUID}/retry"
elif [[ "$CMD" == "retry-all" ]]; then
    curl -sS -X POST "${BASE}/gwas-dlq/retry"
elif [[ "$CMD" == "rerun" ]]; then
    GUID="${1:?Error: GUID required for rerun}"
    curl -sS -X POST "${BASE}/gwas/${GUID}/rerun"
elif [[ "$CMD" == "delete-all" ]]; then
    curl -sS -X DELETE "${BASE}/gwas-dlq"
elif [[ "$CMD" == "delete" ]]; then
    GUID="${1:?Error: GUID required for delete}"
    curl -sS -X DELETE "${BASE}/gwas/${GUID}"
else
    echo "Error: unknown command '$CMD'" >&2
    usage 1
fi
