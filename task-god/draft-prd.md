# Win‑Win Trade Suggestions — Sleeper + FantasyCalc

**Fast path to win‑win trades:** use the **FantasyCalc redraft values** + your **league’s drafted rosters** to quantify each team’s **positional surplus/deficit**, then pair teams with opposite needs and swap players within \~10–12% value delta. Result: realistic, mutually beneficial deals—no guesswork.

---

## Pulling FantasyCalc Rankings Data

* **No direct CSV download** available on the site.
* **API endpoint discovered:** `https://api.fantasycalc.com/values/current`
* **Parameters used:**

  * `isDynasty=false` (redraft leagues)
  * `numQbs=1` (1 QB format)
  * `numTeams=12` (12‑team leagues)
  * `ppr=1` (PPR scoring)

### CSV includes

* Overall & positional rank
* Player name, position, team
* Fantasy value scores (used in trade math)
* Player age, college, experience
* 30‑day trend data
* Tier rankings
* Platform IDs (Sleeper, ESPN, MFL)

This data should be pulled. I believe it comes as a JSON.

---

## Accessing the Sleeper API

* **Docs:** [https://docs.sleeper.com/](https://docs.sleeper.com/)
* **League ID:** 1240782642371104768
* **Roster endpoint example:** `https://api.sleeper.app/v1/league/1240782642371104768/rosters`
* Export to CSV (`sleeper_rosters.csv`) with: owner\_id, display\_name, player\_ids, positions, etc.
* Use this CSV as the input for the workflow below.

## Pulling FantasyCalc Redraft Values (Redraft, 12‑team, 1QB, PPR)

**Source API:** `https://api.fantasycalc.com/values/current`

**Parameters used:**

* `isDynasty=false` (redraft)
* `numQbs=1` (1‑QB leagues)
* `numTeams=12`
* `ppr=1`

## Matching FantasyCalc values with Sleeper rosters

Use the **sleeper\_id** field as the join key. Both the FantasyCalc CSV and the Sleeper API rosters include a Sleeper player ID. Always prefer this over name/position matching, which is error‑prone. The pipeline should:

* Load FantasyCalc CSV with `sleeper_id` column.
* Fetch Sleeper API rosters (which return player\_ids).
* Join on `sleeper_id` to align players between values and rosters.

## What to do (efficient workflow)

**1) Load inputs**

* Values & positions: Pulling FantasyCalc Redraft Values (Redraft, 12‑team, 1QB, PPR)
* Rosters: pull via Sleeper API to a CSV of each team/owner roster.

**2) Model starters + bench**

* Assume redraft 1QB / 2RB / 2WR / 1TE + 1FLEX (RB/WR/TE).
* For each team:

  * Sort players by **value** per position.
  * Sum **starter value** at each position + best bench player as **FLEX**.
  * Everything else at that position = **bench surplus** (tradable capacity).

**3) Quantify needs**

* Compute each team’s **starter value delta** vs league median by position (QB, RB, WR, TE).

  * **Negative delta** = need (e.g., WR‑need).
  * **Positive delta** = strength (e.g., RB‑surplus).

**4) Match partners**

* Pair teams where A has **WR‑need & RB‑surplus** while B has **RB‑need & WR‑surplus** (and likewise for other positions).

**5) Propose deals**

* Prefer 2‑for‑2 deals then 1-for-1 deals.  
* Focus primarily on trades where at least one projected starter is included, so that the trade meaningfully affects each team's starting lineup. 
* Accept only trades with **value difference ≤ \~10–12%** after context nudges (e.g., a trailing team can accept +2–3% “overpay” for upside).

**6) Rank and output**

* Score each trade by **net positional gains** for both teams (improved starter sum) and **fairness** (value delta).
* **Goal:** create **6 trades each week**, with every player in the league involved in one of the trades. This ensures broad participation and balanced improvement across the league.

---

## Example outputs (from the attached files)

Using the attached rosters and the FantasyCalc values, your team ("corey") shows a **mild WR need** and **RB surplus**. These **1‑for‑1, value‑balanced** ideas clear the fairness bar and improve both sides:

* **corey ↔ gabe**

  * **Gabe Receives:** Brian Robinson (RB), Projected RB2. 
  * **Corey Receives:** Jakobi Meyers (WR), Projected FLEX1. 
  * **Fairness:** \~**8.7%** value spread. 
  * **Why it works:** You convert RB depth into a reliable WR starter; Gabe shores up RB depth for weekly stability.

*(Kickers/DST ignored for trade math.)*

---

## Why this is efficient

* **Single pass** per roster to compute starters/surplus.
* **Vectorized** (or SQL‑like) median deltas to flag needs.
* **Greedy pair‑matching** with a simple **≤12% value** constraint yields quick, realistic proposals.
* Extensible to 2‑for‑1s: combine two smaller assets to match one larger value within the same fairness band.
* Ensures **6 balanced trades each week** with full league coverage.

---

## Simplicity for Personal Use

Because this is a personal project for a single league, the implementation can be straightforward:

* One Python script (`weekly_trades.py`).
* One config (league id, paths).
* Weekly run: fetch FantasyCalc + Sleeper rosters, compute starter deltas, generate trades.
* Output: one plain text file ready to copy/paste.

No need for extra layers (equity tracking, CI/CD, multiple league support). Keep dependencies minimal and deterministic.

---

## TL;DR

* Use **FantasyCalc value** as the universal currency.
* Determine **needs vs surplus** by position from your roster file.
* Swap **surplus → need** across teams with **≤10–12% value delta**.
* Output **6 trades per week** so that every owner is included.
* The three examples above are **ready‑to‑propose**.

---

## Weekly plan: **6 trades, all 12 teams involved**

> Assumption: “every player in the league is involved” = **every manager/team participates** (one trade per team each week). Trading *every rostered player* weekly is impractical and harms competitive balance.

### Objective

Produce **exactly six disjoint trades** that (a) pass the fairness band (≤10–12% value delta), (b) improve both teams’ starter sums, and (c) **cover all 12 teams once**.

### Algorithm (one‑shot global matching)

1. **Profile teams**
   Build per‑team needs/surplus (as above) and compute **starter value deltas** vs. league median.

2. **Generate candidate trades**
   For each ordered team pair (A,B), build 1‑for‑1 (and selected 2‑for‑2) proposals that:

   * Swap from **surplus → need** for both sides.
   * Meet fairness (≤12% delta) and both gain ≥X starter points (e.g., ≥3–5 ROS points).
   * Score: `gain_A + gain_B – penalty_fairness – risk_flags`.

3. **Build trade graph**
   Keep only the highest‑scoring trade per pair → weighted graph G.

4. **One‑shot matching**
   Run **maximum‑weight perfect matching** (NetworkX) to select **exactly six disjoint trades**, ensuring all 12 teams are covered. This avoids local optima of looping team‑by‑team.

5. **Relax constraints if needed**
   If no perfect matching exists: widen fairness band, allow limited 2‑for‑1s, or lower min starter‑gain threshold.

6. **Apply policy guardrails**
   Cooldown vs. repeat opponents, star‑player caps, maintain roster integrity.

7. **Output & equity tracking**

   * Publish six trades with deltas and rationales.
   * Log cumulative trade equity to ensure long‑term balance.
   * **Also include a concise starter‑value summary**: show each team’s starter value vs league median by position (QB, RB, WR, TE). This quick table lets managers see needs/surpluses at a glance before reviewing trades.

---

## Output: Starter vs. League Median Snapshot

Provide a **one‑screen summary per team** that compares **starter value** to the **league median** by position. Keep it sortable (CSV) and skimmable (Markdown table for the league post).

### Computation

* **Starter value (pos):** Sum of highest‑value eligible starters at that position (per lineup rules).

  * QB: top 1 QB
  * RB: top 2 RBs
  * WR: top 2 WRs
  * TE: top 1 TE
  * **FLEX:** best remaining RB/WR/TE not already counted
* **TOTAL\_start\_value:** QB + RB + WR + TE + FLEX.
* **League median (pos):** median of all teams’ starter values at that position.
* **Delta\_vs\_median (pos):** `team_pos_value – league_pos_median`.
* **TOTAL\_delta\_vs\_median:** sum of deltas across QB, RB, WR, TE, FLEX.

### CSV schema (for automation)

```
team, qb_start, rb_start, wr_start, te_start, flex_start, total_start,
qb_delta, rb_delta, wr_delta, te_delta, flex_delta, total_delta
```

### League‑post Markdown table (succinct)

| Team | QB Δ | RB Δ | WR Δ | TE Δ | FLEX Δ | TOTAL Δ   |
| ---- | ---- | ---- | ---- | ---- | ------ | --------- |
|      | +6.4 | −3.1 | +8.7 | −1.2 | +2.0   | **+12.8** |
|      | −2.3 | +5.9 | −1.8 | +0.0 | −0.7   | **+1.1**  |

> **Legend:** positive = above median (✅ advantage), negative = below median (⚠️ need). Keep deltas to **one decimal** for readability.

### Notes for the generator

* Round values to **1 decimal**; cap very large positives at **+20.0** in the table and footnote if capped.
* Sort the table by **TOTAL Δ** descending.
* Include a **one‑line summary per team** (e.g., “RB‑heavy, WR‑light”).
* These deltas drive the **edge weights** in the matching graph and the **ChatGPT rationales**.

---

### Practical tips

* **Speed:** limit candidate generation to top **K** bench assets per position (e.g., K=3).
* **Quality:** prefer **1‑for‑1**; use 2‑for‑1 only to fix fairness gaps.
* **Explainability:** always show **starter delta** for both teams; managers approve trades they understand.

---

## TL;DR

* Use FantasyCalc value to price players, compute **needs vs. surplus**, and score candidate swaps.
* Build a team‑to‑team graph with the **best trade** per pair, then run **maximum‑weight perfect matching** to select **six disjoint trades** that involve **all 12 teams**.
* Enforce fairness and policy guardrails; relax constraints only if a perfect matching isn’t possible.

---

## Refined Prompt for ChatGPT Trade Analysis

🔧 **Role and Objective:** You are a fantasy football trade analyst. Evaluate proposed trades for fairness and team improvement.

🔧 **Instructions:** Provide plain-text output only. Use concise, positive language. Limit to under 120 words.

🔧 **Sub-categories:**

* Fairness check: flag trades >12% delta.
* Starter impact: highlight lineup changes.
* Context: mention injuries, bye weeks if relevant.
* Narrative: explain why both teams benefit.

🔧 **Reasoning Steps:**

1. Review trade values and fairness.
2. Compare starter deltas vs. league median.
3. Identify needs filled and surpluses traded.
4. Summarize rationale in 2–3 sentences.

### How ChatGPT adds value

* **Fairness audit:** Ingest each proposed trade, compare player values, flag inequities >12%.
* **Context check:** Weigh injuries, bye weeks, and playoff schedules that raw values miss.
* **Narrative output:** Generate plain-language rationales explaining why each side benefits.
* **Scenario explorer:** Let managers ask "what if we swap Player X instead?" and get instant feedback.
* **Equity tracker:** Maintain memory of each team’s trade history, highlight if one owner consistently gains equity.

### Workflow

1. Run the trade-generation algorithm.
2. Feed the six trades into ChatGPT with context (rosters, values, standings).
3. Receive:

   * Trade summaries (gain/loss, positional impact).
   * League-wide balance report (who improved most, who may be disadvantaged).
   * Alternative suggestions if fairness thresholds fail.

---

## Weekly Python script (automation) — plain text output only

## Accessing ChatGPT API (basics)

* **Docs:** [https://platform.openai.com/docs/api-reference/introduction](https://platform.openai.com/docs/api-reference/introduction)
* **Auth:** set `OPENAI_API_KEY` as environment variable
* **Python SDK:** `pip install openai`
* **Minimal example:**

```
import openai, os
openai.api_key = os.getenv("OPENAI_API_KEY")
resp = openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a fantasy football trade analyst."},
    {"role": "user", "content": "Evaluate trade X for fairness and rationale."}
  ]
)
print(resp.choices[0].message.content)
```

* Use this after trade generation to produce plain-text rationales.

Goal: Run once weekly post-draft (or in-season) and emit a single plain-text report you can copy/paste. No markup, no emojis, no special formatting.

### Dependencies

* Python 3.10+
* pandas, numpy, networkx, requests, python-dateutil

Install:

```
pip install pandas numpy networkx requests python-dateutil
```

### Inputs

* FantasyCalc CSV: path to `fantasycalc_redraft_rankings.csv` (value column used for pricing)
* Sleeper League ID: `1240782642371104768`
* Sleeper rosters endpoint: `https://api.sleeper.app/v1/league/{league_id}/rosters`
* Optional: user/team mapping via `https://api.sleeper.app/v1/league/{league_id}/users`

### CLI

```
python weekly_trades.py \
  --values /path/to/fantasycalc_redraft_rankings.csv \
  --league 1240782642371104768 \
  --out /path/to/weekly_trades.txt
```

### Algorithm steps (implemented in script)

1. Fetch Sleeper rosters/users; build owner -> players.
2. Load FantasyCalc values; join on Sleeper player IDs (fallback to name/position matching where missing).
3. Compute starter sums and deltas vs. league median (QB, RB, WR, TE, FLEX, TOTAL).
4. Generate candidate trades for each team pair (favor 2-for-2; allow 1-for-1 as fallback) that:

   * Move from surplus to need for both sides
   * Pass fairness band (<= 12% value delta)
   * Improve both teams’ starter totals by at least a small threshold (e.g., >= 3.0)
5. Keep the top-scoring candidate per pair; build weighted graph.
6. Run maximum-weight perfect matching (6 disjoint pairs covering all 12 teams). If not possible, relax constraints in order.
7. Emit plain-text report in the exact format below.

### Plain-text output format (exact)

```
LEAGUE STARTER VS MEDIAN SNAPSHOT
team=<TeamName>, qb_delta=<X.X>, rb_delta=<X.X>, wr_delta=<X.X>, te_delta=<X.X>, flex_delta=<X.X>, total_delta=<X.X>
...

RECOMMENDED TRADES (6 TOTAL)
1) <TeamA> sends: <PlayerA1> (<Pos>), <PlayerA2> (<Pos>) ; receives: <PlayerB1> (<Pos>), <PlayerB2> (<Pos>) ; fairness_delta_pct=<X.X>% ; teamA_starter_gain=<X.X> ; teamB_starter_gain=<X.X>
2) ...
...

RATIONALES
1) <TeamA>-<TeamB>: <TeamA> addresses <position_need>, trades from surplus <position_surplus>. <TeamB> addresses <position_need>, trades from surplus <position_surplus>.
2) ...
...

NOTES
- Fairness band <= 12.0%
- Starter gains shown are rest-of-season value deltas
- Positions counted: QB(1), RB(2), WR(2), TE(1), FLEX(1)
```

Rules:

* Plain ASCII only. No tabs; use spaces. One trade per line.
* Round all deltas to one decimal place; fairness\_delta\_pct to one decimal place.
* Team names should match Sleeper display names.
* If fewer than 6 valid trades, list how many found and the reason (e.g., constraints not met), then list "ALTERNATES" with near-miss deals.

### File outputs

* `/path/to/weekly_trades.txt` — the plain-text report (exact format above)
* `/path/to/starter_snapshot.csv` — the per-team deltas table (for your records)

### Minimal script skeleton (pseudocode-style)

```
# weekly_trades.py
import pandas as pd, numpy as np, networkx as nx, requests

def fetch_rosters(league_id):
    r = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters", timeout=30)
    r.raise_for_status()
    rosters = r.json()
    u = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users", timeout=30).json()
    id_to_name = {x.get('user_id'): x.get('display_name') or x.get('username') for x in u}
    # build owner -> list of player_ids
    return rosters, id_to_name

def load_values(csv_path):
    df = pd.read_csv(csv_path)
    # expect columns: sleeper_id (if available), name, position, value, ...
    # normalize names/positions; return lookup by sleeper_id or (name, position)
    return df

# compute_starter_deltas, generate_candidates, score_edges, match_trades, and write_plain_text(...) to be implemented

if __name__ == "__main__":
    # parse args, run pipeline, write outputs
    pass
```

This gives you a repeatable weekly run that produces a single clean text block ready to paste anywhere.
