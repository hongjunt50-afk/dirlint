# dirlint design system

The UI is a printed operations timetable: dense rows under one rule system,
status in a fixed column, totals in a single report line. It is an Operate
surface — the interface should disappear into the audit.

## Color

Restrained: two neutrals, one signal per state. Color never carries meaning
alone; every severity is accompanied by a rule code and a text label.

| Token | Value | Role |
|---|---|---|
| `--paper` | `#F4F2EB` | page ground |
| `--surface` | `#FBFAF5` | bars, hover, expanded row |
| `--ink` | `#171A16` | text, primary button, selected rail |
| `--muted` | `#5F655C` | secondary text, rule codes |
| `--line` | `#D6D3C6` | row and section hairlines |
| `--line-strong` | `#B6B3A5` | structural rules, inputs |
| `--rust` | `#A6402A` | violation stamp, high severity |
| `--amber` | `#8A6118` | medium severity |
| `--green` | `#2C5F47` | clear state |
| `--focus` | `#2F5EA8` | keyboard focus ring |

## Type

One sans family for the interface, one mono for paths, codes, and figures.

- Sans: `ui-sans-serif, "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`
- Mono: `"Cascadia Mono", Consolas, ui-monospace, SFMono-Regular, monospace`
- Scale: 10.5 (signage) / 11.5 / 12.5 / 14 (body) / 20 (totals) / 30 (clear state)
- Signage: uppercase, 0.12–0.14em tracking, 600–650 weight
- Figures: `font-variant-numeric: tabular-nums` everywhere numbers align

## Layout

- Top bar 64px: wordmark, root input, duplicate toggle, primary action.
- Report line: stamp, three totals, timestamp; separated by hairlines, never cards.
- Body: 260px rule index + findings board.
- Rows: 58px code / 1fr path / 300px reason / 96px size.
- Radii: 2px on controls; rows and panels are square. No shadows.

## Components

| Component | Rules |
|---|---|
| Stamp | 1.5px border, uppercase, tracking 0.14em; `HELD` rust, `CLEAR` green |
| Rule index | Rows with code, title, count; selected row is ink-filled, not accented |
| Group head | Sticky, hairline under, rule code + title + count |
| Finding row | Button element; expands in place; `aria-expanded`; reason/fix/full path/copy |
| Buttons | 34px primary, ink fill; 26px secondary outline; hover inverts |
| Inputs | Hairline underline or 1px box, mono for paths, no fill |

## States

Loading: skeleton rows with one sweeping highlight; the Scan button reads
"Scanning…" and is disabled. Empty: green `CLEAR` word plus one sentence.
Error: rust-bordered strip with the message and a retry button. Filtered empty:
the list is simply empty; counts in the toolbar read `0 / N`.

## Motion

150–250ms state transitions only (hover, expansion, count changes). No entrance
choreography. `prefers-reduced-motion: reduce` disables all animation.

## Accessibility

- Text and placeholder contrast ≥ 4.5:1 on paper.
- Visible 2px focus ring, 2px offset.
- `/` focuses the filter from anywhere outside an input.
- Severity is encoded by color plus rule code plus text.
- The findings list is a list of buttons; expansion is controlled by the button.

## Don'ts

- No KPI cards, chart chrome, gradients, glass, or soft-shadowed cards.
- No colored left border on rows; selection is a fill.
- No icon-only controls; every control names its action.
- No serif display face; the timetable world is set in one workhorse sans.
