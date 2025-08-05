CREATE TABLE users(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    paid_until TIMESTAMPTZ,
    trial_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT users_email_check CHECK (email = LOWER(email))
);


CREATE TABLE projects(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects (user_id);


CREATE TABLE active_gmail_thread_ids(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gmail_thread_id TEXT NOT NULL,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_active_gmail_thread_per_user UNIQUE(gmail_thread_id, user_id)
);

CREATE INDEX idx_gmail_thread_id ON active_gmail_thread_ids(gmail_thread_id);
CREATE INDEX idx_gmail_thread_ids_project_ids ON active_gmail_thread_ids(project_id);


CREATE TABLE processed_gmail_msg_ids(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    gmail_msg_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    
    CONSTRAINT unique_proccessed_gmail_msg_per_project UNIQUE(gmail_msg_id, project_id)
);

CREATE TABLE deliverables(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT,
    due_on_desc TEXT,
    spec TEXT,
    is_submitted BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_on TIMESTAMPTZ,
    status_desc TEXT
);

CREATE INDEX idx_deliverables_project_id ON deliverables(project_id);


CREATE TABLE currencies(
    code CHAR(3) PRIMARY KEY,
    full_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(5)
);

INSERT INTO currencies (code, full_name, symbol) VALUES
    ('GBP', 'British Pound', '£'),
    ('USD', 'US Dollar', '$'),
    ('EUR', 'Euro', '€');

CREATE TABLE cost_types(
    code VARCHAR(50) PRIMARY KEY CHECK (code = UPPER(code)),
    full_name VARCHAR(255) NOT NULL
);

INSERT INTO cost_types (code, full_name) VALUES
    ('ANTHROPIC_API_CALL', 'Anthropic API Call');


CREATE TABLE logged_costs(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    currency_code CHAR(3) NOT NULL REFERENCES currencies(code),
    type_code VARCHAR(50) NOT NULL REFERENCES cost_types(code),
    amount NUMERIC(19,4) NOT NULL,
    user_id INT NOT NULL REFERENCES users(id), -- set to admin for platform costs
    project_id INT REFERENCES projects(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_logged_costs_by_user on logged_costs(user_id, created_at DESC);
CREATE INDEX idx_logged_costs_by_project on logged_costs(project_id, created_at DESC);


CREATE OR REPLACE FUNCTION update_updated_at_col()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_col();

CREATE TRIGGER update_deliverables_updated_at 
    BEFORE UPDATE ON deliverables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_col();
