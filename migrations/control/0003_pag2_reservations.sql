-- PAG-2 atomic canary reservations. Owner: hermes_control_owner.
-- Slot uniqueness enforces maximum_exposure without refunds.

CREATE TABLE IF NOT EXISTS adaptation_reservations (
    policy_hash TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    slot_index INTEGER NOT NULL,
    unit_id TEXT NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (policy_hash, approval_id, slot_index)
);

CREATE UNIQUE INDEX IF NOT EXISTS adaptation_reservations_unit
    ON adaptation_reservations (policy_hash, approval_id, unit_id);

INSERT INTO schema_migrations (version) VALUES ('0003_pag2_reservations')
ON CONFLICT DO NOTHING;
