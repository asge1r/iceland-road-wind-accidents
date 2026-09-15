# Figure colour semantics audit

## Decisions and source

The injury palette stays **#79BCE0 minor injury (code 3)** and **#D62728
serious/fatal (codes 1–2)**, recovered from Kristján's `weather_rate.py` in
bfd799f/c90f735. These exact colours do not encode all injury or correction.

Restore coverage count slate #547A99 from the pre-recolouring script at HEAD;
restore traffic response #4C9ED9 from Kristján's c90f735 script. These are
separate count/traffic figures with explicit legends/axes, not injury splits.
They are distinct from the light-blue severity swatch. The coverage line uses
the repository's teal #287271 instead of arbitrary grey. The identical wind
and temperature line remains explicitly identified, not duplicated.

No Kristján-authored original-versus-corrected full-period comparison palette
was recovered: those comparison plots are later additions. Their outline/filled
structure is retained, now in the repository's existing traffic teal #287271,
not grey and not severity red. This is a deliberate documented presentation
choice, not falsely attributed to a recovered supervisor figure.

Restore the vehicle-count category palette GREEN/BLUE/GOLD from HEAD:
#4F8068, #547A99, #D5A444. Maps retain grey for explicitly de-emphasised
reference populations, with gold/teal highlighting linkage or strong wind.

## Every thesis figure

| Figure | Series / meaning | Colours | Source / disposition |
|---|---|---|---|
| 3.1 | Ordinary mapped accidents / strong-wind accidents | Grey #888888 / gold #D89025 | Grey intentionally de-emphasises background; gold avoids severity-red meaning |
| 3.2 | Minor / serious-fatal condition counts | #79BCE0 / #D62728 | Severity source palette |
| 4.1 | Annual all-injury count / matching coverage line | Slate #547A99 / teal #287271 | Count palette restored from HEAD; existing repository teal for coverage |
| 4.2 | Minor / serious-fatal wind O/E | #79BCE0 / #D62728 | Severity palette |
| 4.3 | Minor / serious-fatal gust O/E | #79BCE0 / #D62728 | Severity palette |
| 4.4 | Minor / serious-fatal temperature O/E | #79BCE0 / #D62728 | Severity palette |
| 4.5 | Observed/expected daily traffic | #4C9ED9 | Restored c90f735 traffic-response bars; 100% reference grey |
| 4.6 | Original / corrected all-injury wind O/E | White with teal #287271 outline / filled teal #287271 | Method contrast; deliberate repository traffic palette, not severity encoding |
| 4.7 | Original / corrected all-injury gust O/E | Same outline/filled teal | Same method contrast |
| 4.8 | Corrected minor / serious-fatal O/E | #79BCE0 / #D62728 | Already coloured; retained |
| 4.9 | Earlier-period minor / serious-fatal O/E | #79BCE0 / #D62728 | Severity palette |
| 4.10 | Counter-era minor / serious-fatal O/E | #79BCE0 / #D62728 | Severity palette |
| 4.11 | Corrected counter-era minor / serious-fatal O/E | #79BCE0 / #D62728 | Severity palette |
| 4.12 | Monthly pooled minor / serious-fatal rates | #79BCE0 / #D62728 | Source rate stacks |
| 4.13 | Monthly seasonal wind components | #79BCE0 / #D62728 | Source rate stacks |
| 4.14 | Monthly seasonal gust components | #79BCE0 / #D62728 | Source rate stacks |
| 4.15 | Same-day pooled components | #79BCE0 / #D62728 | Source rate stacks; sensitivity |
| 4.16 | Same-day seasonal wind components | #79BCE0 / #D62728 | Same |
| 4.17 | Same-day seasonal gust components | #79BCE0 / #D62728 | Same |
| 4.18 | Same-day seasonal temperature components | #79BCE0 / #D62728 | Same |
| A.1 | One / two / three-or-more involved vehicles | #4F8068 / #547A99 / #D5A444 | Restored original category palette |
| A.2 | Minor / serious-fatal accident-type proportions | #79BCE0 / #D62728 | Severity palette |
| A.3 | No exact counter link / exact but excluded / retained / counter | #B9BEC2 / #D9A441 / #287271 / #202020 | Existing semantic linkage palette; grey is background |

Reference lines and grids remain grey intentionally. No data bar retains grey
merely for minimalism. No correction uses red. The light-blue severity swatch
never denotes all injury. Distinct slate and traffic-blue colours retain their
original non-severity roles, explicitly named on the corresponding axes.

## Figure numbering in the request

The earlier traffic-response Figure 4.8 is now **4.5**. The earlier
original/corrected Figures 4.5–4.6 are now **4.6–4.7**. Current Figure 4.8 is
the severity comparison and was already light blue/red. Changes follow the
figure's content, not stale numbering.
