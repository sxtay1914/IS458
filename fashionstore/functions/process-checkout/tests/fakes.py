import threading

from service import PaymentResult


class FakePayment:
    def __init__(self, approve=True):
        self.approve = approve
        self.calls = []
        self._lock = threading.Lock()

    def authorize(self, checkout_id, amount_cents, email):
        with self._lock:
            self.calls.append((checkout_id, amount_cents, email))
        return PaymentResult(self.approve, f"pay_{checkout_id[:8]}", None if self.approve else "CARD_DECLINED")


class FakePublisher:
    def __init__(self, fail_times=0):
        self.events = []
        self.fail_times = fail_times
        self._lock = threading.Lock()

    def publish(self, event):
        with self._lock:
            if self.fail_times > 0:
                self.fail_times -= 1
                raise ConnectionError("simulated SNS outage")
            self.events.append(event)
