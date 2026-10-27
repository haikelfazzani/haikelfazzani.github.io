"""Offline application-handler lab, not an MCP transport server.
Run with Python 3.10+: python3 mcp-network-lab.py
No device connections, credentials, or third-party dependencies.
"""
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    subject: str
    writable_devices: frozenset[str]


def tool_result(payload, *, failed=False):
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "structuredContent": payload,
        "isError": failed,
    }


class InterfaceStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._rows = {
            ("edge-07", "eth0"): {"description": "uplink", "revision": 12}
        }

    def snapshot(self, device, interface):
        # Local fixture only; a real resource reader also needs read authorization.
        with self._lock:
            return dict(self._rows[(device, interface)])

    def set_description(self, principal, arguments):
        required = {"device", "interface", "description", "expected_revision"}
        if not isinstance(arguments, dict) or set(arguments) != required:
            return tool_result({"code": "INVALID_ARGUMENTS"}, failed=True)
        device = arguments["device"]
        interface = arguments["interface"]
        text = arguments["description"]
        revision = arguments["expected_revision"]
        if (
            not isinstance(device, str) or not isinstance(interface, str)
            or not isinstance(text, str) or len(text) > 80
            or type(revision) is not int or revision < 0
        ):
            return tool_result({"code": "INVALID_ARGUMENTS"}, failed=True)
        if device not in principal.writable_devices:
            return tool_result({"code": "DENIED"}, failed=True)
        with self._lock:
            row = self._rows.get((device, interface))
            if row is None:
                return tool_result({"code": "NOT_FOUND"}, failed=True)
            if row["revision"] != revision:
                return tool_result({
                    "code": "REVISION_CONFLICT",
                    "current_revision": row["revision"],
                }, failed=True)
            row["description"] = text
            row["revision"] += 1
            return tool_result({"status": "applied", **row})


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.store = InterfaceStore()
        self.writer = Principal("lab-engineer", frozenset({"edge-07"}))
        self.args = {
            "device": "edge-07", "interface": "eth0",
            "description": "uplink to lab-core", "expected_revision": 12,
        }

    def test_apply_and_result(self):
        result = self.store.set_description(self.writer, self.args)
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["revision"], 13)
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])

    def test_permission_denied(self):
        reader = Principal("lab-reader", frozenset())
        result = self.store.set_description(reader, self.args)
        self.assertEqual(result["structuredContent"]["code"], "DENIED")
        self.assertEqual(self.store.snapshot("edge-07", "eth0")["revision"], 12)

    def test_stale_write(self):
        self.store.set_description(self.writer, self.args)
        result = self.store.set_description(self.writer, self.args)
        self.assertEqual(result["structuredContent"]["code"], "REVISION_CONFLICT")
        self.assertEqual(self.store.snapshot("edge-07", "eth0")["revision"], 13)

    def test_bad_arguments(self):
        for change in ({"description": "x" * 81}, {"expected_revision": True},
                       {"expected_revision": -1}, {"extra": "ignored?"}):
            with self.subTest(change=change):
                result = self.store.set_description(self.writer, {**self.args, **change})
                self.assertEqual(result["structuredContent"]["code"], "INVALID_ARGUMENTS")

    def test_missing_interface(self):
        result = self.store.set_description(self.writer, {**self.args, "interface": "missing"})
        self.assertEqual(result["structuredContent"]["code"], "NOT_FOUND")

    def test_snapshot_is_a_copy(self):
        snapshot = self.store.snapshot("edge-07", "eth0")
        snapshot["revision"] = 999
        self.assertEqual(self.store.snapshot("edge-07", "eth0")["revision"], 12)

    def test_concurrent_writers(self):
        barrier = threading.Barrier(2)
        def write(description):
            barrier.wait(timeout=5)
            return self.store.set_description(self.writer, {**self.args, "description": description})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, ["writer A", "writer B"]))
        self.assertEqual(sum(not result["isError"] for result in results), 1)
        self.assertEqual(self.store.snapshot("edge-07", "eth0")["revision"], 13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
