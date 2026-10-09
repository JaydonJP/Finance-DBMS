-- 12 SYSTEM-SPECIFIC READ-ONLY ORACLE SQL QUERIES
-- Prerequisites: 01_schema.sql -> 03_plsql.sql -> 02_seed.sql

-- Q01: Household members and derived ages
SELECT h.name AS household, u.user_id, u.name AS member,
       TRUNC(MONTHS_BETWEEN(SYSDATE, u.dob) / 12) AS age
FROM PF_HOUSEHOLD h JOIN PF_USERS u ON u.household_id = h.household_id
ORDER BY h.name, u.name;

-- Q02: Account owners, banks and balances
SELECT a.account_id, a.owner_name, a.owner_type,
       a.bank_name, a.acc_type, a.balance
FROM PF_ACCOUNT_OVERVIEW a
ORDER BY a.account_id;

-- Q03: Investment portfolio and market values
SELECT u.name AS investor, c.name AS company,
       s.share_id, us.quantity, s.market_price,
       us.quantity * s.market_price AS holding_value
FROM PF_USER_SHARES us
JOIN PF_USERS u ON u.user_id = us.user_id
JOIN PF_SHARES s ON s.share_id = us.share_id
JOIN PF_COMPANY c ON c.company_id = s.company_id
ORDER BY u.name, c.name;

-- Q04: Total spending by expense category
SELECT c.name AS category, COUNT(*) AS transaction_count,
       SUM(t.amount) AS total_spent
FROM PF_TRANSACTION t JOIN PF_CATEGORY c ON c.category_id = t.category_id
WHERE t.trans_type = 'EXPENSE'
GROUP BY c.name
ORDER BY total_spent DESC;

-- Q05: Accounts above average balance
SELECT a.account_id, a.balance
FROM PF_ACCOUNT a
WHERE a.balance > (SELECT AVG(balance) FROM PF_ACCOUNT)
ORDER BY a.balance DESC;

-- Q06: Savings goal progress using PL/SQL function
SELECT g.goal_id, c.name AS goal_category,
       g.current_amt, g.target_amt,
       PF_GOAL_PROGRESS(g.goal_id) AS progress_percent
FROM PF_GOAL g JOIN PF_CATEGORY c ON c.category_id = g.category_id
ORDER BY progress_percent DESC;

-- Q07: Monthly-equivalent subscription cost per account
SELECT a.account_id, COUNT(s.subscription_id) AS subscriptions,
       ROUND(SUM(CASE s.bill_cycle
           WHEN 'WEEKLY' THEN s.amount * 52 / 12
           WHEN 'MONTHLY' THEN s.amount
           WHEN 'YEARLY' THEN s.amount / 12
       END), 2) AS monthly_equivalent
FROM PF_ACCOUNT a JOIN PF_SUBSCRIPTION s ON s.account_id = a.account_id
GROUP BY a.account_id
ORDER BY monthly_equivalent DESC;

-- Q08: Companies and employee counts (includes zero)
SELECT c.company_id, c.name AS company,
       COUNT(u.user_id) AS employee_count
FROM PF_COMPANY c LEFT JOIN PF_USERS u ON u.employer_company_id = c.company_id
GROUP BY c.company_id, c.name
ORDER BY employee_count DESC, c.name;

-- Q09: Largest expense of each account (correlated subquery)
SELECT t.account_id, t.trans_id, t.amount, c.name AS category
FROM PF_TRANSACTION t JOIN PF_CATEGORY c ON c.category_id = t.category_id
WHERE t.trans_type = 'EXPENSE'
  AND t.amount = (
      SELECT MAX(x.amount) FROM PF_TRANSACTION x
      WHERE x.account_id = t.account_id AND x.trans_type = 'EXPENSE'
  )
ORDER BY t.account_id, t.trans_id;

-- Q10: Monthly personal income and expenses
SELECT u.name AS user_name, TO_CHAR(t.trans_date, 'YYYY-MM') AS period_month,
       SUM(CASE WHEN t.trans_type = 'INCOME' THEN t.amount ELSE 0 END) AS income,
       SUM(CASE WHEN t.trans_type = 'EXPENSE' THEN t.amount ELSE 0 END) AS expenses
FROM PF_USERS u
JOIN PF_ACCOUNT a ON a.user_id = u.user_id
JOIN PF_TRANSACTION t ON t.account_id = a.account_id
GROUP BY u.name, TO_CHAR(t.trans_date, 'YYYY-MM')
ORDER BY u.name, period_month;

-- Q11: Bank-wise total balances including empty banks
SELECT b.name AS bank_name, COUNT(a.account_id) AS accounts,
       NVL(SUM(a.balance), 0) AS total_balance
FROM PF_BANK b LEFT JOIN PF_ACCOUNT a ON a.bank_id = b.bank_id
GROUP BY b.bank_id, b.name
ORDER BY total_balance DESC;

-- Q12: Transaction audit trail maintained by trigger
SELECT audit_id, trans_id, action_name,
       old_amount, new_amount, changed_at
FROM PF_TRANS_AUDIT
ORDER BY audit_id DESC;

