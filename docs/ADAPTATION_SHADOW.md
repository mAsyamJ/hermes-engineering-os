# Adaptation Shadow

Shadow is mandatory before canary. It answers: had this policy been active,
what would it have done?

It does not change Hermes execution, Kanban rows, models, profiles, skills,
or prompts. It does not claim candidate efficacy.

Production shadow reads Kanban through the existing `mode=ro` adapter.
Fixture policies typically do not match production boards (`NOT_ELIGIBLE`),
which is the honest result. Decision latency is recorded.
