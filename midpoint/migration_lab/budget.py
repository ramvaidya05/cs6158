"""Conservative pre-call spend reservations; failed/unknown calls retain reservation."""
import json
import math
from .storage import save_json
from .backends import BackendError


class SpendBudget:
    def __init__(self, limit, input_rate, output_rate, path=None):
        if any(not math.isfinite(x) or x <= 0 for x in (limit, input_rate, output_rate)):
            raise ValueError("Positive finite dollar limit and token prices required")
        self.limit, self.input_rate, self.output_rate = limit, input_rate, output_rate
        self.entries, self.path = [], path

    def record(self):
        result = {"limit_usd": self.limit, "accounted_usd": sum(x["accounted_usd"] for x in self.entries),
                  "input_usd_per_million": self.input_rate, "output_usd_per_million": self.output_rate,
                  "policy": "UTF-8 request bytes + 4096 overhead as conservative input-token allowance; "
                            "1.25x input rate reserves cache-write premium; unknown charges retain full reservation. "
                            "Estimate at supplied prices, not a provider billing guarantee.", "calls": self.entries}
        if self.path:
            save_json(self.path, result)
        return result

    def reserve(self, body):
        allowance = len(json.dumps(body, ensure_ascii=False).encode()) + 4096
        if allowance > 272000:
            raise BackendError("Prompt exceeds small-experiment pricing tier", "budget")
        dollars = (allowance * self.input_rate * 1.25 + body["max_output_tokens"] * self.output_rate) / 1e6
        if self.record()["accounted_usd"] + dollars > self.limit:
            raise BackendError("Experiment dollar reservation budget exhausted", "budget")
        entry = {"reserved_usd": dollars, "accounted_usd": dollars, "usage_known": False}
        self.entries.append(entry)
        self.record()
        return len(self.entries) - 1

    def settle(self, reservation, usage):
        if not isinstance(usage, dict):
            return
        counts = [usage.get("input_tokens"), usage.get("output_tokens")]
        if any(type(x) is not int or x < 0 for x in counts):
            return
        # Deliberately overestimate cached tokens at the full rate plus cache-write premium.
        cost = (counts[0] * self.input_rate * 1.25 + counts[1] * self.output_rate) / 1e6
        self.entries[reservation].update(accounted_usd=cost, usage_known=True, usage=usage)
        self.record()


class PartitionedBudget(SpendBudget):
    """Preallocated per-trial/arm envelopes; unused funds never move between arms."""
    def __init__(self, original, planned, max_repairs, max_output_tokens):
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError('Positive integer output-token limit required')
        if type(max_repairs) is not int or max_repairs < 0:
            raise ValueError('Nonnegative integer repair limit required')
        if original.entries:
            raise ValueError('A partitioned experiment requires a fresh budget')
        super().__init__(original.limit, original.input_rate, original.output_rate)
        # Existing reserve() rejects requests above 272,000 input allowance.
        # Fund every admitted call at that bound before any network request.
        per_call = (272000 * self.input_rate * 1.25 + max_output_tokens * self.output_rate) / 1e6
        self.allocations = {item['path']: per_call * (1 if item['arm'] == 'one_shot' else max_repairs)
                            for item in planned}
        self.required_limit = sum(self.allocations.values())
        if self.required_limit > self.limit + 1e-12:
            raise ValueError(f'Fair allocation needs a reservation limit of at least ${self.required_limit:.6f}; '
                             f'configured ${self.limit:.6f}. Reduce trials/repair rounds or explicitly raise the cap. '
                             'No model request was made; reservations are not predicted charges.')
        self.active = None

    def activate(self, key):
        if key not in self.allocations:
            raise ValueError('Unknown budget allocation')
        self.active = key

    def record(self):
        result = super().record()
        result['allocation_policy'] = 'Fixed independent trial/arm envelopes; initial candidate paid once; unused allocations never transferred'
        result['required_reservation_usd'] = self.required_limit
        result['allocations'] = {key: {'limit_usd':limit,
            'accounted_usd':sum(e['accounted_usd'] for e in self.entries if e.get('allocation') == key)}
            for key,limit in self.allocations.items()}
        if self.path:
            save_json(self.path,result)
        return result

    def reserve(self, body):
        if self.active is None:
            raise BackendError('No active trial/arm allocation', 'budget')
        allowance = len(json.dumps(body,ensure_ascii=False).encode()) + 4096
        dollars = (allowance*self.input_rate*1.25 + body['max_output_tokens']*self.output_rate)/1e6
        used = sum(e['accounted_usd'] for e in self.entries if e.get('allocation') == self.active)
        if used+dollars > self.allocations[self.active]+1e-12:
            raise BackendError('This trial/arm allocation is exhausted; other arms remain funded', 'budget')
        reservation = super().reserve(body)
        self.entries[reservation]['allocation'] = self.active
        self.record()
        return reservation
