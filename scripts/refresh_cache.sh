#!/bin/bash
set -e

curl -X POST "http://localhost:8000/api/v1/internal/clear-cache"
echo "Cache cleared"

curl "http://localhost:8000/api/v1/info/gpmap_metadata"
curl "http://localhost:8000/api/v1/search/options"

# Array of study IDs to set cache for
study_ids=(
    2608 1284 3763 3680 2007 1641 2582 2591 938 931
    2606 2588 4503 1630 3613 932 4452 2581 1632 919
    1996 1995 3814 1624 1636 921 1988 1980 2613 920
    924 2585 923 1981 1622 2624 3424 1638 1623 1640
    3090 2583 1985 2382 928 1986 1983 3775 2477 1481
    1982 937 3584 1647 3342 2383 2379 4286 926 4400
    3759 4241 3699 935 2384 4353 3748 3693 2586 2625
    2587 1992 4303 3219 3743 1984 3448 1644 1987 3709
    4472 3744 3242 3499 3395 3084 1989 4532 3516 3265
    3143 3464 2006 168 2869 1993
)

for study_id in "${study_ids[@]}"; do
    echo "Setting associations cache for: $study_id"
    curl "http://localhost:8000/api/v1/traits/$study_id?include_associations=true"
done
