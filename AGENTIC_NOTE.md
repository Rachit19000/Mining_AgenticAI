# What makes this system agentic?

MineOps Agent is agentic because the flow of control is decided at runtime based
on the user's question, not hard-coded per query.

For every request the agent:

1. **Interprets intent** — parses the question and detects the target zone and
   topic (safety, equipment, gas, ranking, shift summary).
2. **Plans** — builds an ordered list of steps it intends to take and exposes it.
3. **Selects tools dynamically** — invokes only the tools needed for that intent.
   Asking about maintenance calls the equipment tool; asking "is Zone B safe"
   chains gas → incidents → equipment through the action-plan tool.
4. **Reasons over results** — combines evidence into a risk score and level.
5. **Chains further calls when needed** — e.g. a gas question first checks
   readings, then generates a full action plan if levels are elevated.
6. **Acts within guardrails** — refuses to fabricate missing data and defers to
   emergency protocols on danger-level readings.
7. **Reports transparently** — logs every tool call and returns a confidence
   score.

Different questions therefore produce different tool sequences:

- "Which equipment needs urgent maintenance?" → `inspect_equipment_status`
- "Which zone should be inspected first?" → `rank_zone_risk`
- "Is Zone B safe?" → `generate_supervisor_action_plan` (gas + incidents + equipment)

That dynamic, evidence-driven tool selection — rather than a single fixed script —
is what makes it an agent rather than a chatbot.
