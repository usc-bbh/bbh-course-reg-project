# Runtime analysis (supplied Google Sheet, joined to the output audit)

- Source workbook: `runtime_sheet.xlsx` — sheets: Overview, Majors Detail, Minors Detail, Run Summary
- Per-page rows parsed: **288** (majors 207, minors 81)
- Rows joined to an audited output file: **288/288**

Note from the workbook's own Overview sheet: the majors run completed all 207 pages; the minors run stopped at page 82 of 263 on a verification challenge. The sheet therefore covers 289 page-scrapes, not the full 470-file corpus.

## Distribution of per-page runtime

| n | min | Q1 | median | mean | Q3 | IQR | 1.5×IQR fence | max | stdev |
|---|---|---|---|---|---|---|---|---|---|
| 288 | 0s | 5s | 7s | 50.2s | 84s | 79s | 202s | 962s | 83.1s |

## Slowest 15 pages

```
majors/159 Neuroscience Ba                                  962s browser_rendered_dom PASS
majors/161 Non Governmental Organizations And Social        230s browser_rendered_dom PASS
majors/124 History Ba                                       219s browser_rendered_dom PASS
majors/181 Political Science Ba                             206s browser_rendered_dom REVIEW
majors/175 Philosophy Politics And Law Ba                   201s browser_rendered_dom PASS
majors/188 Religion Ba                                      201s browser_rendered_dom REVIEW
majors/120 Global Health Studies Bs                         200s browser_rendered_dom REVIEW
majors/133 Intelligence And Cyber Operations Ba             200s browser_rendered_dom PASS
majors/144 Law History And Culture Ba                       200s browser_rendered_dom PASS
majors/122 Health And Human Sciences Ba                     199s browser_rendered_dom PASS
majors/142 Latin American And Iberian Cultures Media        198s browser_rendered_dom PASS
majors/201 Visual And Performing Arts Studies Ba            198s browser_rendered_dom PASS
majors/135 International Relations Ba                       194s browser_rendered_dom PASS
majors/155 Music Industry Bs                                194s browser_rendered_dom REVIEW
majors/160 Neuroscience Bs                                  189s browser_rendered_dom REVIEW
```

## Statistical outliers (> 202s, i.e. Q3 + 1.5×IQR): 4 pages

```
majors/159 Neuroscience Ba                                  962s browser_rendered_dom PASS
majors/161 Non Governmental Organizations And Social        230s browser_rendered_dom PASS
majors/124 History Ba                                       219s browser_rendered_dom PASS
majors/181 Political Science Ba                             206s browser_rendered_dom REVIEW
```

## Does runtime predict a defective output?

- FAIL pages (n=66): median **7s**, mean 28.1s
- PASS pages (n=189): median **6s**, mean 49.6s
- Of the 4 slowest-outlier pages, **0** produced a FAIL output (0%).
- **34 of 66** FAIL pages ran at or below the median runtime — i.e. most contaminated outputs came from *fast* scrapes.

**Conclusion: runtime does not predict contamination.** Slow pages are explained by bot-wall escalation to the browser layer; the contamination is a deterministic extraction defect that occurs at full speed on plain HTTP 200 responses.

## Failure clustering

By corpus:

| bucket | pages | FAIL | FAIL rate | median runtime |
|---|---|---|---|---|
| majors | 207 | 36 | 17% | 28s |
| minors | 81 | 30 | 37% | 5s |

By acquisition method:

| bucket | pages | FAIL | FAIL rate | median runtime |
|---|---|---|---|---|
| direct_html | 180 | 35 | 19% | 5s |
| browser_rendered_dom | 108 | 31 | 29% | 126s |

By degree type:

| bucket | pages | FAIL | FAIL rate | median runtime |
|---|---|---|---|---|
| BS | 95 | 11 | 12% | 7s |
| BA | 82 | 23 | 28% | 38s |
| MINOR | 81 | 30 | 37% | 5s |
| BFA | 15 | 1 | 7% | 117s |
| BM | 13 | 0 | 0% | 142s |
| BARCH | 1 | 0 | 0% | 5s |
| BSW | 1 | 1 | 100% | 53s |

## 107 Environmental Science and Health (BA)

- Sheet row: page 107 (majors), method `browser_rendered_dom`, **75s**
- z-score vs all pages: **+0.30** — within the normal range
- Percentile: **73th**

It was slow (browser escalation after the bot-wall), but *not* uniquely slow, and many pages that ran longer produced perfectly clean output. Runtime is a symptom of the bot-wall, not the cause of the defect.
