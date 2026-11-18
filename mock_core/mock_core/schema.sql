CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(16) PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(16) PRIMARY KEY,
    account_number VARCHAR(24) NOT NULL,
    address VARCHAR(128) NOT NULL,
    phone_number VARCHAR(24) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS agent_customer (
    agent_id VARCHAR(16) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    PRIMARY KEY (agent_id, customer_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS loan_contracts (
    contract_id VARCHAR(16) PRIMARY KEY,
    customer_id VARCHAR(16) NOT NULL,
    product VARCHAR(64) NOT NULL,
    principal_yen BIGINT UNSIGNED NOT NULL,
    disbursed_on DATE NOT NULL,
    status VARCHAR(16) NOT NULL,
    is_pair_loan TINYINT UNSIGNED NOT NULL,
    UNIQUE KEY (customer_id, contract_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS repayment_schedule (
    contract_id VARCHAR(16) NOT NULL,
    period SMALLINT UNSIGNED NOT NULL,
    due_date DATE NOT NULL,
    amount_yen BIGINT UNSIGNED NOT NULL,
    principal_yen BIGINT UNSIGNED NOT NULL,
    interest_yen BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (contract_id, period),
    FOREIGN KEY (contract_id) REFERENCES loan_contracts(contract_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS repayment_history (
    contract_id VARCHAR(16) NOT NULL,
    period SMALLINT UNSIGNED NOT NULL,
    paid_on DATE NOT NULL,
    PRIMARY KEY (contract_id, period),
    FOREIGN KEY (contract_id, period) REFERENCES repayment_schedule(contract_id, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS delinquencies (
    contract_id VARCHAR(16) PRIMARY KEY,
    customer_id VARCHAR(16) NOT NULL,
    days_overdue SMALLINT UNSIGNED NOT NULL,
    amount_yen BIGINT UNSIGNED NOT NULL,
    late_fee_yen BIGINT UNSIGNED NOT NULL,
    FOREIGN KEY (customer_id, contract_id) REFERENCES loan_contracts(customer_id, contract_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS rate_terms (
    contract_id VARCHAR(16) PRIMARY KEY,
    annual_rate_percent DECIMAL(6, 3) NOT NULL,
    rate_type VARCHAR(32) NOT NULL,
    fixed_until DATE,
    insurance_type VARCHAR(32) NOT NULL,
    insurance_increment_percent DECIMAL(6, 3) NOT NULL,
    FOREIGN KEY (contract_id) REFERENCES loan_contracts(contract_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS benefits (
    customer_id VARCHAR(16) NOT NULL,
    name VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    PRIMARY KEY (customer_id, name),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;
