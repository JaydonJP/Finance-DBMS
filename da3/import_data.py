"""Idempotent standalone fixture import; never overwrites existing demo records."""
from database import initialize,reconciliation

if __name__=='__main__':
    print('Imported fresh dataset.' if initialize() else 'Dataset already initialized; records preserved.')
    for row in reconciliation():
        assert row['actual_paise']==row['expected_paise'],row
    print('All account balances reconcile with their opening balances and ledgers.')
