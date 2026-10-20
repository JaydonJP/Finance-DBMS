// Neo4j Community 2026.09.0; safe to rerun.
CREATE CONSTRAINT household_key IF NOT EXISTS FOR (n:Household) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT company_key IF NOT EXISTS FOR (n:Company) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT bank_key IF NOT EXISTS FOR (n:Bank) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT category_key IF NOT EXISTS FOR (n:Category) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT user_key IF NOT EXISTS FOR (n:User) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT account_key IF NOT EXISTS FOR (n:Account) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT share_key IF NOT EXISTS FOR (n:Share) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT subscription_key IF NOT EXISTS FOR (n:Subscription) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT goal_key IF NOT EXISTS FOR (n:Goal) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT transaction_key IF NOT EXISTS FOR (n:Transaction) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT auditevent_key IF NOT EXISTS FOR (n:AuditEvent) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT demostate_key IF NOT EXISTS FOR (n:DemoState) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT category_name IF NOT EXISTS FOR (n:Category) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT holding_key IF NOT EXISTS FOR ()-[h:HOLDS]-() REQUIRE h.key IS UNIQUE;
CREATE INDEX transaction_date IF NOT EXISTS FOR (t:Transaction) ON (t.trans_date);
// Required values, ownership and relationship cardinality are application rules.
