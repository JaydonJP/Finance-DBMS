-- RUN AFTER 01_schema.sql AND BEFORE 02_seed.sql.
-- The audit/balance trigger is created before sample transactions are inserted.

-- A row-level trigger: INSERT/UPDATE/DELETE on transactions updates account balance.
-- The CHECK(balance >= 0) constraint also blocks overspending and rolls back the DML.
CREATE OR REPLACE TRIGGER PF_TRANSACTION_BALANCE_TRG
AFTER INSERT OR UPDATE OR DELETE ON PF_TRANSACTION
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        UPDATE PF_ACCOUNT
        SET balance = balance +
            CASE WHEN :NEW.trans_type = 'INCOME' THEN :NEW.amount ELSE -:NEW.amount END
        WHERE account_id = :NEW.account_id;

        INSERT INTO PF_TRANS_AUDIT(audit_id, trans_id, action_name, old_amount, new_amount)
        VALUES (PF_AUDIT_SEQ.NEXTVAL, :NEW.trans_id, 'INSERT', NULL, :NEW.amount);

    ELSIF UPDATING THEN
        IF :OLD.account_id = :NEW.account_id THEN
            -- Apply the net change at once, avoiding a temporary negative balance.
            UPDATE PF_ACCOUNT
            SET balance = balance
                - CASE WHEN :OLD.trans_type = 'INCOME' THEN :OLD.amount ELSE -:OLD.amount END
                + CASE WHEN :NEW.trans_type = 'INCOME' THEN :NEW.amount ELSE -:NEW.amount END
            WHERE account_id = :NEW.account_id;
        ELSE
            -- If moved to another account, reverse the old and apply the new.
            UPDATE PF_ACCOUNT
            SET balance = balance -
                CASE WHEN :OLD.trans_type = 'INCOME' THEN :OLD.amount ELSE -:OLD.amount END
            WHERE account_id = :OLD.account_id;

            UPDATE PF_ACCOUNT
            SET balance = balance +
                CASE WHEN :NEW.trans_type = 'INCOME' THEN :NEW.amount ELSE -:NEW.amount END
            WHERE account_id = :NEW.account_id;
        END IF;

        INSERT INTO PF_TRANS_AUDIT(audit_id, trans_id, action_name, old_amount, new_amount)
        VALUES (PF_AUDIT_SEQ.NEXTVAL, :NEW.trans_id, 'UPDATE', :OLD.amount, :NEW.amount);

    ELSIF DELETING THEN
        UPDATE PF_ACCOUNT
        SET balance = balance -
            CASE WHEN :OLD.trans_type = 'INCOME' THEN :OLD.amount ELSE -:OLD.amount END
        WHERE account_id = :OLD.account_id;

        INSERT INTO PF_TRANS_AUDIT(audit_id, trans_id, action_name, old_amount, new_amount)
        VALUES (PF_AUDIT_SEQ.NEXTVAL, :OLD.trans_id, 'DELETE', :OLD.amount, NULL);
    END IF;
END;
/

-- PL/SQL function: calculates percentage completion of a savings goal.
CREATE OR REPLACE FUNCTION PF_GOAL_PROGRESS(p_goal_id IN NUMBER)
RETURN NUMBER
IS
    v_current PF_GOAL.current_amt%TYPE;
    v_target  PF_GOAL.target_amt%TYPE;
BEGIN
    SELECT current_amt, target_amt
    INTO v_current, v_target
    FROM PF_GOAL
    WHERE goal_id = p_goal_id;

    RETURN ROUND(100 * v_current / v_target, 2);
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN NULL;
END;
/

-- PL/SQL procedure: create a transaction with a sequence-based ID.
-- Balance update and audit insertion happen automatically via the trigger.
CREATE OR REPLACE PROCEDURE PF_ADD_TRANSACTION(
    p_account_id IN NUMBER,
    p_category_id IN NUMBER,
    p_trans_type IN VARCHAR2,
    p_amount IN NUMBER,
    p_trans_id OUT NUMBER
)
IS
BEGIN
    IF p_amount <= 0 OR p_amount IS NULL THEN
        RAISE_APPLICATION_ERROR(-20001, 'Amount must be positive');
    END IF;

    SELECT PF_TRANS_SEQ.NEXTVAL INTO p_trans_id FROM DUAL;

    INSERT INTO PF_TRANSACTION(trans_id, account_id, category_id,
                               trans_date, trans_type, amount)
    VALUES (p_trans_id, p_account_id, p_category_id,
            SYSDATE, UPPER(p_trans_type), p_amount);
END;
/

-- Explicit parameterized cursor: display transaction history for one account.
CREATE OR REPLACE PROCEDURE PF_PRINT_ACCOUNT_HISTORY(p_account_id IN NUMBER)
IS
    CURSOR tx_cur IS
        SELECT trans_id, trans_date, trans_type, amount
        FROM PF_TRANSACTION
        WHERE account_id = p_account_id
        ORDER BY trans_date, trans_id;
BEGIN
    FOR r IN tx_cur LOOP
        DBMS_OUTPUT.PUT_LINE(
            'TX ' || r.trans_id || ' | ' || TO_CHAR(r.trans_date, 'DD-MON-YYYY') ||
            ' | ' || r.trans_type || ' | ' || r.amount
        );
    END LOOP;
END;
/

-- A view combines account and owner details, covered in Experiment 6.
CREATE OR REPLACE VIEW PF_ACCOUNT_OVERVIEW AS
SELECT a.account_id, a.acc_type, a.balance,
       CASE WHEN a.user_id IS NOT NULL THEN u.name ELSE c.name END AS owner_name,
       CASE WHEN a.user_id IS NOT NULL THEN 'USER' ELSE 'COMPANY' END AS owner_type,
       b.name AS bank_name
FROM PF_ACCOUNT a
LEFT JOIN PF_USERS u ON u.user_id = a.user_id
LEFT JOIN PF_COMPANY c ON c.company_id = a.company_id
JOIN PF_BANK b ON b.bank_id = a.bank_id;

-- Check for invalid objects after script execution:
SELECT object_name, object_type, status
FROM user_objects
WHERE object_name LIKE 'PF_%'
ORDER BY object_type, object_name;
