-- PERSONAL FINANCE & INVESTMENT MANAGEMENT SYSTEM (Oracle SQL)
-- RUN ONCE in an Oracle schema. Objects deliberately start with PF_ to avoid lab table collisions.
-- Do NOT rerun CREATE TABLE statements without resetting these project objects.

CREATE TABLE PF_HOUSEHOLD (
    household_id NUMBER(6) PRIMARY KEY,
    name         VARCHAR2(80) NOT NULL
);

CREATE TABLE PF_COMPANY (
    company_id NUMBER(6) PRIMARY KEY,
    name       VARCHAR2(100) NOT NULL,
    industry   VARCHAR2(70) NOT NULL
);

CREATE TABLE PF_BANK (
    bank_id     NUMBER(6) PRIMARY KEY,
    name        VARCHAR2(80) NOT NULL,
    branch_code VARCHAR2(20) NOT NULL
);

CREATE TABLE PF_CATEGORY (
    category_id NUMBER(6) PRIMARY KEY,
    name        VARCHAR2(80) UNIQUE NOT NULL
);

CREATE TABLE PF_USERS (
    user_id             NUMBER(6) PRIMARY KEY,
    name                VARCHAR2(80) NOT NULL,
    dob                 DATE NOT NULL,
    household_id        NUMBER(6) NOT NULL,
    employer_company_id NUMBER(6),
    CONSTRAINT pf_user_house_fk FOREIGN KEY (household_id)
        REFERENCES PF_HOUSEHOLD(household_id),
    CONSTRAINT pf_user_employer_fk FOREIGN KEY (employer_company_id)
        REFERENCES PF_COMPANY(company_id)
);

CREATE TABLE PF_ACCOUNT (
    account_id NUMBER(8) PRIMARY KEY,
    acc_type   VARCHAR2(20) NOT NULL,
    balance    NUMBER(14,2) DEFAULT 0 NOT NULL,
    user_id    NUMBER(6),
    company_id NUMBER(6),
    bank_id    NUMBER(6) NOT NULL,
    CONSTRAINT pf_account_type_ck CHECK (acc_type IN ('SAVINGS','CURRENT')),
    CONSTRAINT pf_account_bal_ck CHECK (balance >= 0),
    -- A personal account has a user; a corporate account has a company (not both).
    CONSTRAINT pf_account_owner_ck CHECK (
        (user_id IS NOT NULL AND company_id IS NULL) OR
        (user_id IS NULL AND company_id IS NOT NULL)
    ),
    CONSTRAINT pf_account_user_fk FOREIGN KEY (user_id)
        REFERENCES PF_USERS(user_id),
    CONSTRAINT pf_account_company_fk FOREIGN KEY (company_id)
        REFERENCES PF_COMPANY(company_id),
    CONSTRAINT pf_account_bank_fk FOREIGN KEY (bank_id)
        REFERENCES PF_BANK(bank_id)
);

CREATE TABLE PF_SHARES (
    share_id     NUMBER(8) PRIMARY KEY,
    company_id   NUMBER(6) NOT NULL,
    market_price NUMBER(12,2) NOT NULL,
    CONSTRAINT pf_shares_price_ck CHECK (market_price >= 0),
    CONSTRAINT pf_shares_company_fk FOREIGN KEY (company_id)
        REFERENCES PF_COMPANY(company_id)
);

-- Junction table for the ER diagram's M:N USERS--OWNS--SHARES relationship.
CREATE TABLE PF_USER_SHARES (
    user_id  NUMBER(6) NOT NULL,
    share_id NUMBER(8) NOT NULL,
    quantity NUMBER(10) NOT NULL,
    CONSTRAINT pf_holdings_pk PRIMARY KEY (user_id, share_id),
    CONSTRAINT pf_holdings_qty_ck CHECK (quantity > 0),
    CONSTRAINT pf_holdings_user_fk FOREIGN KEY (user_id)
        REFERENCES PF_USERS(user_id),
    CONSTRAINT pf_holdings_share_fk FOREIGN KEY (share_id)
        REFERENCES PF_SHARES(share_id)
);

-- SUBSCRIPTION is shown as a weak entity in DA1: scoped ID per account.
CREATE TABLE PF_SUBSCRIPTION (
    account_id      NUMBER(8) NOT NULL,
    subscription_id NUMBER(6) NOT NULL,
    name            VARCHAR2(80) NOT NULL,
    bill_cycle      VARCHAR2(20) NOT NULL,
    amount          NUMBER(10,2) NOT NULL,
    CONSTRAINT pf_sub_pk PRIMARY KEY (account_id, subscription_id),
    CONSTRAINT pf_sub_amount_ck CHECK (amount > 0),
    CONSTRAINT pf_sub_cycle_ck CHECK (bill_cycle IN ('WEEKLY','MONTHLY','YEARLY')),
    CONSTRAINT pf_sub_account_fk FOREIGN KEY (account_id)
        REFERENCES PF_ACCOUNT(account_id)
);

CREATE TABLE PF_GOAL (
    goal_id      NUMBER(8) PRIMARY KEY,
    account_id   NUMBER(8) NOT NULL,
    category_id  NUMBER(6) NOT NULL,
    current_amt  NUMBER(14,2) DEFAULT 0 NOT NULL,
    target_amt   NUMBER(14,2) NOT NULL,
    CONSTRAINT pf_goal_cur_ck CHECK (current_amt >= 0),
    CONSTRAINT pf_goal_target_ck CHECK (target_amt > 0),
    CONSTRAINT pf_goal_acc_fk FOREIGN KEY (account_id)
        REFERENCES PF_ACCOUNT(account_id),
    CONSTRAINT pf_goal_cat_fk FOREIGN KEY (category_id)
        REFERENCES PF_CATEGORY(category_id)
);

CREATE TABLE PF_TRANSACTION (
    trans_id    NUMBER(8) PRIMARY KEY,
    account_id  NUMBER(8) NOT NULL,
    category_id NUMBER(6) NOT NULL,
    trans_date  DATE DEFAULT SYSDATE NOT NULL,
    trans_type  VARCHAR2(12) NOT NULL,
    amount      NUMBER(14,2) NOT NULL,
    CONSTRAINT pf_tx_type_ck CHECK (trans_type IN ('INCOME','EXPENSE')),
    CONSTRAINT pf_tx_amount_ck CHECK (amount > 0),
    CONSTRAINT pf_tx_acc_fk FOREIGN KEY (account_id)
        REFERENCES PF_ACCOUNT(account_id),
    CONSTRAINT pf_tx_cat_fk FOREIGN KEY (category_id)
        REFERENCES PF_CATEGORY(category_id)
);

-- Supporting audit table, not a DA1 entity; demonstrates DML audit using a trigger.
CREATE TABLE PF_TRANS_AUDIT (
    audit_id    NUMBER(10) PRIMARY KEY,
    trans_id    NUMBER(8) NOT NULL,
    action_name VARCHAR2(10) NOT NULL,
    old_amount  NUMBER(14,2),
    new_amount  NUMBER(14,2),
    changed_at  DATE DEFAULT SYSDATE NOT NULL
);

CREATE SEQUENCE PF_TRANS_SEQ START WITH 1000 INCREMENT BY 1;
CREATE SEQUENCE PF_AUDIT_SEQ START WITH 1 INCREMENT BY 1;

-- Expected: 12 tables (11 design tables + audit) and 2 sequences.
SELECT table_name FROM user_tables WHERE table_name LIKE 'PF_%' ORDER BY table_name;
