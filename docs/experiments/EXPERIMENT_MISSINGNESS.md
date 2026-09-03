# Experiment Missingness

Track assigned N, started N, completed N, primary-known N, missing N.

Unknown outcomes stay explicit. Primary ITT never silently drops missing
units. Completers-only is exploratory only.

If missingness exceeds the pre-registered threshold after the horizon,
conclusion is INSUFFICIENT_DATA or INVALIDATED according to the protocol
(`on_exceed`).

Units that never start remain in assigned N.
