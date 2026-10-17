
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL
        CHECK (role IN ('employee', 'monitoring_admin')),
    token_hash TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_balances (
    employee_id TEXT NOT NULL
        REFERENCES employees(employee_id),
    leave_type TEXT NOT NULL,
    available_days INTEGER NOT NULL
        CHECK (available_days >= 0),
    as_of_date DATE NOT NULL,
    PRIMARY KEY (employee_id, leave_type)
);

CREATE TABLE IF NOT EXISTS leave_proposals (
    proposal_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL
        REFERENCES employees(employee_id),
    action_type TEXT NOT NULL DEFAULT 'leave_request'
        CHECK (action_type = 'leave_request'),
    leave_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    business_days INTEGER NOT NULL
        CHECK (business_days > 0),
    reason TEXT,
    validation_summary JSONB NOT NULL DEFAULT '[]',
    expires_at TIMESTAMPTZ NOT NULL,
    requires_confirmation BOOLEAN NOT NULL DEFAULT TRUE
        CHECK (requires_confirmation = TRUE),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    request_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL UNIQUE
        REFERENCES leave_proposals(proposal_id),
    employee_id TEXT NOT NULL
        REFERENCES employees(employee_id),
    leave_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    business_days INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_manager_review'
        CHECK (status = 'pending_manager_review'),
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_leave_requests_employee
    ON leave_requests(employee_id);

CREATE TABLE IF NOT EXISTS hr_tickets (
    ticket_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL
        REFERENCES employees(employee_id),
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    version TEXT NOT NULL,
    effective_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL
        REFERENCES policy_documents(document_id),
    title TEXT NOT NULL,
    section TEXT NOT NULL,
    version TEXT NOT NULL,
    effective_date DATE NOT NULL,
    content TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', content)
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_policy_chunks_search
    ON policy_chunks USING GIN(search_vector);

CREATE TABLE IF NOT EXISTS agent_traces (
    trace_id TEXT PRIMARY KEY,
    employee_id TEXT
        REFERENCES employees(employee_id),
    outcome TEXT,
    trace_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
