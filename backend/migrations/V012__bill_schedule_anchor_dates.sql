-- Preserve the intended day-of-month when advancing schedules across short months.
ALTER TABLE recurring_bills ADD COLUMN schedule_day INTEGER NOT NULL DEFAULT 1;
ALTER TABLE recurring_bills ADD COLUMN schedule_month INTEGER;
