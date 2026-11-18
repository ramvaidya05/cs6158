import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from migration_lab.budget import SpendBudget, PartitionedBudget
from migration_lab.backends import BackendError
from migration_lab.experiments import run_experiment
from scripts.audit_cli_scope import audit


class BudgetTests(unittest.TestCase):
    def budget(self, repairs=1):
        planned = [{'path': arm, 'arm': arm} for arm in ('one_shot', 'basic', 'operation')]
        return PartitionedBudget(SpendBudget(10, .75, 3.75), planned, repairs, 32768)

    def test_preflight_rejects_before_artifacts_or_calls(self):
        backend = Mock(budget=SpendBudget(.01, .75, 3.75))
        suite = Mock()
        suite.identity.return_value = {'counts': {'commons_cli': 1}}
        with patch('migration_lab.experiments.new_run') as create:
            with self.assertRaisesRegex(ValueError, 'No model request'):
                run_experiment(backend, suite, tasks=('commons_cli',), feedback_ablation=True)
        create.assert_not_called()
        backend.generate.assert_not_called()

    def test_independent_allocations_in_either_order(self):
        body = {'max_output_tokens': 32768, 'prompt': 'x' * 250000}
        for order in [('basic', 'operation'), ('operation', 'basic')]:
            budget = self.budget()
            for arm in order:
                budget.activate(arm)
                index = budget.reserve(body)
                budget.settle(index, None)  # Unknown usage retains reservation.
                with self.assertRaises(BackendError):
                    budget.reserve(body)
            self.assertEqual(len(budget.entries), 2)
            self.assertFalse(any(row['usage_known'] for row in budget.entries))

    def test_settlement_and_saved_ledger_are_local(self):
        budget = self.budget()
        with tempfile.TemporaryDirectory() as tmp:
            budget.path = Path(tmp) / 'spend.json'
            budget.activate('basic')
            index = budget.reserve({'max_output_tokens': 32768})
            budget.settle(index, {'input_tokens': 10, 'output_tokens': 10})
            saved = json.loads(budget.path.read_text())
        self.assertGreater(saved['allocations']['basic']['accounted_usd'], 0)
        self.assertEqual(saved['allocations']['operation']['accounted_usd'], 0)
        self.assertEqual(saved['allocations']['basic']['limit_usd'], saved['allocations']['operation']['limit_usd'])

    def test_zero_repairs_cannot_spend_on_repair(self):
        budget = self.budget(repairs=0)
        budget.activate('basic')
        with self.assertRaises(BackendError):
            budget.reserve({'max_output_tokens': 1})
        budget.activate('one_shot')
        budget.reserve({'max_output_tokens': 32768})

    def test_used_budget_rejected(self):
        original = SpendBudget(10, .75, 3.75)
        original.reserve({'max_output_tokens': 1})
        with self.assertRaisesRegex(ValueError, 'fresh'):
            PartitionedBudget(original, [], 1, 1)


class ScopeTests(unittest.TestCase):
    def test_exception_stops_reach_count_and_return_alias_tracks_type(self):
        contract = {'source_artifact': 'fixture', 'source_files': [], 'excluded': [], 'candidate_scope': 'fixture',
                    'classes': {'A': {'constructor': {'args': []}, 'methods': {
                        'alias': {'returns': 'A'}, 'fail': {'returns': 'void'}, 'later': {'returns': 'void'}}}}}
        operations = [{'op': 'new', 'class': 'A', 'save': 'a'},
                      {'op': 'call', 'on': 'a', 'method': 'alias', 'save': 'b'},
                      {'op': 'call', 'on': 'b', 'method': 'fail'},
                      {'op': 'call', 'on': 'b', 'method': 'later'}]
        data = {'cases': [{'id': 'c', 'operations': operations}], 'reference': [{'id': 'c', 'trace': [
            {'step': 0, 'status': 'ok'}, {'step': 1, 'status': 'ok'}, {'step': 2, 'status': 'exception'}]}]}
        result = audit(contract, {'tasks': {'commons_cli': {'visible': data}}})['splits']['visible']
        self.assertEqual(result['methods_reached'], 2)
        self.assertEqual(result['api']['A.fail']['exception'], 1)
        self.assertEqual(result['api']['A.later'], dict(scheduled=1, reached=0, normal=0, exception=0))
