# MineOps Agent — Agentic AI Assistant for Mining Operations

MineOps Agent is a small **agentic AI** system for the mining sector. A supervisor
asks a question in plain language; the agent interprets the intent, **decides which
tools it needs**, calls them against structured mining data, reasons over the
results, and returns a grounded risk assessment and recommended actions.

```
Supervisor → question → MineOps Agent → selects tools → analyzes data → risk + action plan
```

The agent runs **fully offline and deterministically** on the Python standard
library (no LLM API key required), which makes it safe, testable, and reproducible.

---

## Architecture

```
┌──────────────────┐
│  Supervisor      │
└────────┬─────────┘
         ↓  question
┌──────────────────┐
│  MineOps Agent   │   agent/agent.py
│  intent + plan   │   - detects zone / intent
└────────┬─────────┘   - builds a tool plan
         ↓  dynamic tool selection
 ┌───────────────┬────────────────────┬─────────────────────┐
 ↓               ↓                    ↓                     ↓
check_gas_levels inspect_equipment_ summarize_incidents  rank_zone_risk
                 status                                  generate_supervisor_
                                                         action_plan
 └───────────────┴────────────────────┴─────────────────────┘
         ↓  structured results
┌──────────────────┐
│  Guardrails      │   agent/guardrails.py
│  no fabrication  │   - missing data → say so
│  no override     │   - danger → emergency notice
└────────┬─────────┘
         ↓
   Risk level + evidence + action plan + confidence + tool log
```

### Project structure

```
mineops-agent/
├── data/                       # structured sample data (JSON)
│   ├── gas_readings.json
│   ├── equipment.json
│   └── incidents.json
├── agent/
│   ├── config.py               # thresholds & data paths (single source of truth)
│   ├── data_store.py           # loads JSON (swap for SQLite later)
│   ├── tools.py                # the 5 agent tools
│   ├── guardrails.py           # anti-fabrication + emergency protocol rules
│   └── agent.py                # intent detection, planning, execution, logging
├── tests/
│   ├── test_gas.py             # tests check_gas_levels + guardrail
│   ├── test_equipment.py       # tests inspect_equipment_status + guardrail
│   └── test_agent.py           # tool-selection + safe/unsafe eval examples
├── main.py                     # CLI chat interface
├── app.py                      # optional Streamlit UI (bonus)
├── requirements.txt
└── README.md
```

---

## Setup

```bash
git clone <your-repo-url>
cd mineops-agent

# (optional) create a virtualenv
python -m pip install -r requirements.txt
```

The core agent needs no third-party packages. `pytest` is used for tests and
`streamlit` is optional for the web UI.

---

## Usage

### CLI

```bash
# interactive chat
python main.py

# single question
python main.py "Is Zone B safe for workers right now?"

# run the built-in example questions
python main.py --demo
```

### Web UI (bonus)

```bash
pip install streamlit
streamlit run app.py
```

---

## The 5 tools

| Tool | Purpose |
|------|---------|
| `check_gas_levels(zone)` | Classifies methane / CO / temperature / dust against thresholds. |
| `inspect_equipment_status(zone=None)` | Flags equipment needing maintenance by status and operating hours. |
| `summarize_incidents(zone=None)` | Summarizes incident records, sorted by severity. |
| `rank_zone_risk()` | Scores every zone by combined gas + incident + equipment risk. |
| `generate_supervisor_action_plan(zone)` | Combines all evidence into a grounded action plan and risk level. |

---

## What makes this system agentic?

The system is agentic because it does **not** follow a fixed sequence for every
question. It interprets the request, decides which tools are required, invokes
only those tools, evaluates the results, and chains additional tool calls when
needed before producing the final answer.

Different questions → different tool sequences:

| Question | Tools selected |
|----------|----------------|
| "Which equipment needs urgent maintenance?" | `inspect_equipment_status` |
| "Which zone should be inspected first?" | `rank_zone_risk` |
| "Is Zone B safe right now?" | `generate_supervisor_action_plan` → (gas + incidents + equipment) |
| "Are there risks from the last shift?" | `summarize_incidents` + `inspect_equipment_status` |

The agent also **plans** (lists its intended steps), **logs every tool call**, and
returns a **confidence score** based on how much data was available.

### Example: "Is Zone B safe for workers right now?"

```
Intent: zone_safety
Plan:
  1. Check current gas readings
  2. Check recent incidents
  3. Check ventilation / equipment status
  4. Calculate risk and generate an action plan
Tool calls:
  [OK] generate_supervisor_action_plan(zone=Zone B)
----------------------------------------------------------------------
Risk Level: HIGH
Evidence:
  - methane=1.8 (danger)
  - carbon_monoxide=15 (warning)
  - High-severity Gas Alert at 2026-09-24 09:30
  - Ventilation Fan HV-101 status=warning (Reduced airflow)
Recommended actions:
  - Restrict worker access to Zone B.
  - Have qualified safety personnel assess the situation on site.
  - Re-check methane readings and follow the mine's gas/emergency protocol.
  - Inspect the ventilation system and confirm airflow is restored.

<emergency notice deferring to established protocol>
Confidence: 1.0
```

---

## Safety guardrails

Safety is enforced in code (`agent/guardrails.py`), not left to chance:

1. **No fabricated readings.** Tools read only from the data files. If a zone has
   no records, the tool raises `MissingDataError` and the agent reports
   *"No gas readings available for Zone X. Cannot assess this factor"* instead of
   guessing a value.
2. **No overriding emergency protocols.** When any reading reaches its danger
   threshold, the response attaches an emergency notice telling the supervisor to
   follow the mine's established protocol and involve qualified safety personnel.
   The agent never says "levels are high but work can continue."
3. **Human authority preserved.** The assistant is explicitly framed as decision
   *support*, not a replacement for regulated procedures or supervisors.
4. **Single source of truth for thresholds.** All limits live in `config.py`.

> The thresholds in this demo are illustrative. A real deployment must use the
> mine's own regulated safety limits.

---

## Tests

```bash
python -m pytest -q
```

Coverage:
- `test_gas.py` — `check_gas_levels` values/classification + no-fabrication guardrail.
- `test_equipment.py` — `inspect_equipment_status` flagging + unknown-zone guardrail.
- `test_agent.py` — dynamic tool selection, and **safe vs unsafe** evaluation
  examples (Zone A = LOW, Zone B = HIGH with emergency notice, unknown zone =
  honest missing-data response).

All 13 tests pass.

---

## Sample data

- **Zones:** Zone A (safe), Zone B (elevated methane + warning fan), Zone C
  (critical conveyor + high CO).
- **Equipment:** drillers, haul trucks, ventilation fans, conveyor belts — with
  status, operating hours, last service, and fault reports.
- **Sensors:** methane, carbon monoxide, temperature, dust per zone.
- **Incidents:** gas alert, equipment overheating, roof fall warning, worker injury.

---

## Extending

- Swap `data_store.py` JSON loaders for SQLite without touching the tools.
- Add RAG over historical incident PDFs for "have we seen this before?" queries.
- Plug in an LLM for tool selection while keeping the same tool + guardrail layer.
