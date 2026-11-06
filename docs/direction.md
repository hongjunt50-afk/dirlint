# Direction contract — dirlint web UI

Mode: Operate (web). Build path: code-led.

THESIS
A printed operations timetable for a workspace: dense rows under one rule system,
status in a fixed column, totals in a single report line. Refuses KPI cards,
chart chrome, and card grids.

OWN-WORLD
Bone paper (#F4F2EB) and near-black ink (#171A16); one signal rust (#A6402A) for
violations, deep green (#2C5F47) for clear, amber (#8A6118) for medium severity;
hairline rules (#D6D3C6) instead of shadows; monospaced paths and figures;
uppercase 10.5px signage with 0.12–0.14em tracking; square corners (2px max).

STORY
Open → see whether the workspace is clear → see how many and what kind → filter
by rule or search → expand a row for the full path, reason, and fix → rescan
after cleanup.

FIRST VIEWPORT
64px top bar: wordmark left, root path input and Scan button right. Below, one
report line: status stamp, findings / reclaimable / elapsed, timestamp at the far
right. Then a 236px rule index on the left, and the findings board filling the
rest of the viewport.

FORM
Transit timetable / operations board; 7th of 7 grounded directions.
seed: c854a8c70b67f8ab

FINISH
Reviewed at 1440 (desktop only; no mobile surface is shipped); unreviewed and undocumented is unfinished.
