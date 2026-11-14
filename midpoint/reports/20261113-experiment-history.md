# Experiment history

Each admitted batch is separate. No pooled semantic accuracy is calculated. Different subjects, protocols, repeated candidates, and infrastructure failures are not independent samples. Accounting includes failed and integrity-invalid experiment calls; standalone diagnostics are outside this catalog. Accounted dollars are conservative reservations, not measured charges.

| Archive | Model / provenance | Study | One-shot | Code repair | Environment repair | Calls |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 20261019T223008Z-experiment-7991f91c | gpt-5.6-sol | natural_translation | 0/3 | 0/3 | 0/3 | 3 |
| 20261019T223104Z-experiment-80feac8d | synthetic_fixture | controlled_environment_stress | 0/1 | 0/1 | 1/1 | 0 |
| 20261019T224716Z-experiment-5942d812 | gemini-3.8-flash | natural_translation | 2/3 | 2/3 | 2/3 | 3 |
| 20261019T225222Z-experiment-b8857705 | gemini-3.8-flash | natural_translation | 3/3 | 3/3 | 3/3 | 3 |
| 20261111T232307Z-experiment-6d8f99ec | gemini-3.8-flash | natural_translation | 0/9 | 0/9 | 0/9 | 8 |
| 20261112T014615Z-recorded-gemini-stress-f10fc0f9 | saved_model_response | controlled_environment_stress | 1/1 | 0/1 | 1/1 | 0 |
| 20261113T225208Z-experiment-f7ea06a7 | gemini-3.8-flash | natural_translation | 0/6 | 0/6 | 0/6 | 2 |
| 20261113T235626Z-experiment-78be7f18 | gemini-3.8-flash | natural_translation | 0/6 | 0/6 | 0/6 | 3 |

Scores above are operational task/trial passes over all admitted trials. An unavailable or unrun trial earns no operational pass; it is not an observed incorrect translation.

## 20261019T223008Z-experiment-7991f91c

Verified 47 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| levenshtein | 0/3 | 0 | 0 |

## 20261019T223104Z-experiment-80feac8d

Verified 84 files. Provenance: `synthetic_fixture`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| levenshtein | 1/1 | 0 | 1 |

## 20261019T224716Z-experiment-5942d812

Verified 217 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| levenshtein | 2/3 | 2 | 0 |

## 20261019T225222Z-experiment-b8857705

Verified 293 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| levenshtein | 3/3 | 3 | 0 |

## 20261111T232307Z-experiment-6d8f99ec

Verified 131 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| jaro_winkler | 0/3 | 0 | 0 |
| levenshtein | 0/3 | 0 | 0 |
| normalized | 0/3 | 0 | 0 |

## 20261112T014615Z-recorded-gemini-stress-f10fc0f9

Verified 80 files. Provenance: `saved_model_response`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| levenshtein | 1/1 | 1 | 0 |

## 20261113T225208Z-experiment-f7ea06a7

Verified 57 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| jaro_winkler | 0/3 | 0 | 0 |
| normalized | 0/3 | 0 | 0 |

Provider stop: `budget`.

## 20261113T235626Z-experiment-78be7f18

Verified 57 files. Provenance: `live_model`.

| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |
| --- | ---: | ---: | ---: |
| jaro_winkler | 0/3 | 0 | 0 |
| normalized | 0/3 | 0 | 0 |

Provider stop: `provider_unavailable`.
