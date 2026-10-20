# DA3 plan: Personal Finance and Investment Relationship Analysis using Neo4j

Status: implemented. See `da3/README.md`, the verified report and the source package
in `da3/submission/`. The original proposal below records the design rationale;
the delivered build includes complete CRUD and all 12 original reports plus 3 graph insights.
Deadline: today, 20 October 2026. No prescribed report template or page limit.

## Selection and justification

Use Neo4j Community Edition, in the Graph Database category explicitly listed in
the assignment. Retain personal finance as the application domain and extend it
with household and investment relationship analysis.

The reason to choose a graph here is the connected domain: households contain
users; users own accounts, work at companies, and hold shares issued by companies.
Graph pattern queries make these connections explicit and support useful
questions about shared investments and concentration of financial exposure.
Neo4j models entities as labeled nodes and connections as typed relationships
with properties [1].

This is a use-case-specific justification. Oracle remains a good fit for ledger
records, tabular reporting, declarative integrity rules, and PL/SQL. We will not
claim that Neo4j is universally faster or that SQL cannot answer graph questions.
The comparison will show the query structure and explain the modeling tradeoffs.
Any performance figures must come from actual, documented measurements.

## Scope for today's submission

- A standalone Flask application backed by Neo4j, in a new `da3/` directory.
- Preserve DA2 and its Oracle data for reference and comparison.
- Represent all existing business entities and import the fictional sample data.
- Demonstrate create/read/update/delete for users and transactions, plus updating
  investment holdings. Provide read views for the remaining entities.
- Implement six familiar reports: account balances/owners, spending by category,
  monthly income/expenses, investment valuation, goal progress, and audit history.
- Add three graph-specific insights and a graph view through Neo4j Browser.
- Provide launch/stop scripts, verification, a report, and a short demo script.

Additional CRUD screens or the remaining original reports are optional extensions
after the required demo works. No additional database, AI API, or graph plugin
is needed for the proposed core features.

## Architecture

```text
Browser -> DA3 Flask app (127.0.0.1:5001)
        -> official Neo4j Python driver / parameterized Cypher
        -> Neo4j Community in Ubuntu WSL / Podman
        -> persistent Neo4j data volume

Neo4j Browser (127.0.0.1:7474) -> visual exploration and live Cypher queries
```

Use the existing WSL environment, with a pinned official Neo4j Community image
and localhost-only ports. Neo4j documents an official container image and the
Browser/Bolt ports [2]; validate the image under this PC's Podman installation.
Normal demo operation should work offline after installation and seeding.
Oracle is not needed while running DA3. Run one database at a time when possible
to reduce memory usage on this PC.

## Graph schema and relational mapping

| DA2 concept | Neo4j representation |
|---|---|
| PF_HOUSEHOLD | Household node |
| PF_USERS | User node; User MEMBER_OF Household |
| Employer foreign key | User WORKS_AT Company |
| PF_COMPANY | Company node |
| PF_BANK | Bank node |
| PF_ACCOUNT | Account node; User or Company OWNS Account; Account HELD_AT Bank |
| PF_SHARES | Share node; Company ISSUES Share |
| PF_USER_SHARES | User HOLDS Share relationship, with quantity property |
| PF_SUBSCRIPTION | Subscription node; Account HAS_SUBSCRIPTION Subscription |
| PF_GOAL | Goal node; Account HAS_GOAL Goal; Goal IN_CATEGORY Category |
| PF_CATEGORY | Category node |
| PF_TRANSACTION | Transaction node; Account HAS_TRANSACTION Transaction; Transaction IN_CATEGORY Category |
| PF_TRANS_AUDIT | AuditEvent node with transaction ID and old/new snapshots |

Preserve existing business IDs. Give subscriptions a stable key derived from
account ID and subscription ID, because their ID is only unique within an account.
Give holdings a stable user/share pair key to prevent duplicate HOLDS relationships.
An AuditEvent must retain its transaction ID even after the Transaction is deleted.

Add uniqueness constraints for stable identifiers. Community Edition supports
property uniqueness constraints; required fields, positive amounts, allowed types,
relationship cardinalities, and ownership rules need explicit application
validation rather than assuming Oracle CHECK/FOREIGN KEY rules carry over [3].

Store monetary values as integer paise and format them as rupees in the UI.
Preserve dates as dates. Retain opening balances and reconcile current balances
against the ledger during import and verification.

## Core operations and integrity

1. Add, display, edit, and delete a temporary user.
2. Create an income/expense transaction linked to an existing account/category.
3. Update or delete that transaction and reverse/apply its balance effect.
4. Add/update a holding relationship and calculate portfolio value.
5. Reject duplicate IDs, missing references, invalid amounts, overspending,
   and deletion of entities still required by other records.

For each transaction mutation, perform validation, account balance changes,
transaction changes, and audit creation in one managed Neo4j write transaction.
Acquire account write locks before reading balances; use a stable account order
when a transaction moves between accounts. Retried transaction callbacks must
not perform external side effects. The Python driver supports managed atomic
transactions [4]. Do not present these operations as Oracle PL/SQL triggers.

## Three graph-specific queries

1. **Employer-investment overlap:** find users who work for a company and hold
   shares issued by that same company. Explain concentration of salary and
   investment exposure; this is an informational indicator, not financial advice.
2. **Household company exposure:** follow Household <- MEMBER_OF - User - HOLDS
   -> Share <- ISSUES - Company to aggregate a household's holdings by company.
3. **Shared investment connections:** find pairs of users who hold shares in
   common and return the connecting paths for graph visualization.

These queries work with relationships already present in the project and do not
require inventing a fraud-detection application or adding an embedding service.
Use graph output as well as tabular results so the technology is visible in the demo.

## Dataset and import

- Start from the original fictional dataset: 3 households, 5 users, 7 accounts,
  12 transactions, and its existing companies, shares, holdings, categories,
  goals and subscriptions.
- Create portable CSV or JSON fixtures and a repeatable Python importer using
  stable IDs. DA3 must not require a live Oracle instance to seed or run.
- Account 1001 must reconcile to 66800 rupees after the original seed events.
- Do not both import the final balance and apply all seed transaction deltas again.
- Add a few explicitly documented fictional examples only if needed to clarify
  a graph query. Keep any extra dataset separate from baseline reconciliation.
- Re-running import must not duplicate nodes, relationships or balance effects.
- Reset demo data only through an explicit reset operation scoped to the DA3 store.

## Build order and completion checks

| Phase | Work | Evidence before moving on |
|---|---|---|
| 1 | Install Neo4j, define model/constraints, create fixture/importer | Persistent database, expected counts, correct balances, repeatable import |
| 2 | Build Neo4j data access and core CRUD | All writes reach Neo4j; invalid writes roll back; audit survives transaction deletion |
| 3 | Add six reports and three graph queries | Known expected results and visible graph paths |
| 4 | Verify launcher/restart and capture evidence | Offline launch, persistent records, clean sample data |
| 5 | Finish report and rehearse | Screenshots, comparison, runnable commands, 5-minute demo |

Complete the essential implementation before adding cosmetic changes. If time
is constrained, prioritize correctness, observable graph queries and submission
evidence over additional screens.

## Report outline

Aim for approximately 8-12 pages unless faculty provides a different expectation.
Use the DA2 report, if supplied, to retain the correct student details and context.

1. Title and abstract.
2. Existing application and DA3 objectives.
3. Selected database category, Neo4j justification and alternatives considered.
4. Property graph diagram, node/relationship properties, IDs and constraints.
5. Implementation architecture and reproducible setup.
6. Dataset, import process and reconciliation.
7. CRUD demonstrations and Cypher query results, with screenshots.
8. Oracle vs Neo4j comparison: representation, query structure, integrity,
   transactions, visualization, and limitations.
9. Actual test outcomes, conclusion and references.

Capture screenshots from the completed application and database. Do not describe
planned features or unperformed tests as implemented results.

## Five-minute demonstration

1. Show the application dashboard and explain the selected database category.
2. Show a household/user/account/company graph in Neo4j Browser.
3. Add a temporary user, edit it, and remove it.
4. Add a 250-rupee expense to account 1001: 66800 -> 66550. Change it to
   300 rupees: 66500. Delete it: 66800. Show the audit events.
5. Run employer-investment overlap and household company exposure; show paths.
6. Show one equivalent SQL and Cypher query and explain the tradeoffs.

## References checked while planning

1. [Neo4j property graph concepts](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
2. [Official Neo4j container setup](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
3. [Cypher and Neo4j editions/constraints](https://neo4j.com/docs/cypher-manual/current/introduction/cypher-neo4j/)
4. [Neo4j Python managed transactions](https://neo4j.com/docs/python-manual/current/transactions/)
