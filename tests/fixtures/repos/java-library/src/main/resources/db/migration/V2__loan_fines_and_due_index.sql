-- Fines are computed when a copy comes back late (FineCalculator) and kept on the loan.
ALTER TABLE loans ADD COLUMN fine_cents BIGINT NOT NULL DEFAULT 0 CHECK (fine_cents >= 0);

-- The daily reminder sweep scans open loans by due date.
CREATE INDEX loans_open_due_on ON loans (due_on) WHERE returned_on IS NULL;
