---
title: "MCP at the Edge of a Commit"
description: "A visual research note on Model Context Protocol and network control: ASCII diagrams, protocol traces, and a tested Python experiment on concurrent writes."
publishedDate: 2026-03-12
---

*Research note · Haikel Fazzani · Diagrams, protocol traces, and a local experiment*

An assistant inspects a failing link and proposes a change. Its arguments validate. Before execution, another controller modifies the device. Is the original operation still justified?

That small interval is the subject of this note: **how Model Context Protocol connects an AI application to infrastructure, and what the application must still enforce.**

## Where MCP sits

MCP standardizes discovery and access to external capabilities. The **host** coordinates the model and permissions; each **client** connects to a **server**, which exposes a focused interface. A server does not need to contain a model. [Architecture](https://modelcontextprotocol.io/specification/2025-06-18/architecture)

```text
                 AI APPLICATION / HOST
  +------------------------------------------------+
  | Operator <--> Model                            |
  |                  | proposed operation          |
  |                  v                             |
  |             Host policy                        |
  |               /      \                         |
  |        MCP client A   MCP client B              |
  +-------------|--------------|-------------------+
                |              |
           MCP server A   MCP server B
           network tools  documentation
                |
          Device adapter
                |
          Router / switch
```

Here the server is a gateway; it could instead run on the device. Either placement still needs device-specific semantics.

The three server primitives serve different purposes. Resources supply URI-addressed context; tools expose callable operations; prompts supply reusable message templates. [Resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources), [tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools), [prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

```text
RESOURCE                 TOOL                    PROMPT
"What can I inspect?"    "What can I invoke?"    "How shall we investigate?"
        |                        |                        |
interface snapshot       set description         troubleshoot a link
routing state            validate a change       review a configuration
        |                        |                        |
     context                  operation                template

A listed operation is not a permission grant.
```

## A session on the wire

The examples pin MCP to **2025-06-18**, the revision referenced by the network draft. They are original illustrations, not a claim about the latest protocol version.

```text
Client                                   Server
  |                                         |
  | initialize(version, capabilities) -----> |
  | <----- selected version + capabilities  |
  |                                         |
  | [check that the version is supported]   |
  | notifications/initialized ------------> |
  |                                         |
  | tools/list ---------------------------> |
  | <-------------------- tool definitions  |
  |                                         |
  | tools/call(name, arguments) -----------> |
  | <------------------------- tool result  |
```

Initialization negotiates version and capabilities before normal operation. The ready notification expects no response. [Lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)

A concrete call, after negotiation and discovery:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "lab.interface.set_description",
    "arguments": {
      "device": "edge-07",
      "interface": "eth0",
      "description": "uplink to lab-core",
      "expected_revision": 12
    }
  }
}
```

`id` correlates a request and response. It is not a durable change identifier. The tool name and `expected_revision` are local design choices used below.

```text
Same JSON-RPC messages; different transport boundaries

stdio           client -- stdin/stdout --> subprocess
                one message per line; logs on stderr

Streamable HTTP client -- POST /mcp -----> server
                JSON or event-stream responses
                negotiated version header
                session header if assigned
```

The HTTP request must accept both JSON and event streams. The JSON above is a message body, not a complete HTTP exchange. [Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

## Reading the network draft

[Draft-zeng-mcp-network-mgmt-01](https://www.ietf.org/archive/id/draft-zeng-mcp-network-mgmt-01.html) proposes a network capability, CLI/YANG tools, configuration commits, rollback, and network resources. Published in October 2025, revision `-01` expired on April 19, 2026. It remains work in progress, not an RFC.

A few details need reconciliation with the referenced MCP revision:

```text
Draft wording                 MCP 2025-06-18 baseline
---------------------------   ---------------------------------
serverCapabilities            initialize result.capabilities
available=false on a tool     absent from the core tool definition
subscription cursor           subscriptions != paginated listings
```

These are interoperability questions, not established MCP behavior. Compare the [draft](https://www.ietf.org/archive/id/draft-zeng-mcp-network-mgmt-01.html) with the [lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle), [tool definition](https://modelcontextprotocol.io/specification/2025-06-18/server/tools), and [resource protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/resources).

For a prototype, I would document a private schema under the negotiated `experimental` capability space. That is a design choice using an [existing extension point](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle#capability-negotiation), not a new standard.

My larger concern is semantic: two devices can advertise the same operation while disagreeing about locking, persistence, or recovery. A common tool name cannot erase those differences.

## A write that can refuse

The experiment permits one operation: changing an interface description. No arbitrary CLI, routing edits, or port shutdowns. Its input schema requires four fields:

```json
{
  "type": "object",
  "properties": {
    "device": { "type": "string" },
    "interface": { "type": "string" },
    "description": { "type": "string", "maxLength": 80 },
    "expected_revision": { "type": "integer", "minimum": 0 }
  },
  "required": ["device", "interface", "description", "expected_revision"],
  "additionalProperties": false
}
```

Authorization context comes from the trusted server boundary. A model-supplied `role: "admin"` proves nothing. MCP’s HTTP authorization flow addresses access tokens; device-level policy remains an application concern. [Authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

```text
                  Two writers, one observation

       Writer A                           Writer B
       read revision 12                   read revision 12
              |                                  |
       propose "uplink A"                 propose "uplink B"
              |                                  |
              v                                  v
       +-----------------------------------------------+
       |              ATOMIC BOUNDARY                  |
       | compare expected revision -> apply -> advance |
       +-----------------------------------------------+
              |                                  |
       accepted: revision 13              rejected: stale 12

Either writer may win. Both must not succeed against revision 12.
```

After validation and permission checks, the handler’s critical section is:

```python
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
```

Moving the comparison outside the lock reintroduces the race. A Python lock protects this process only: a real adapter needs device-supported conditional writes or locking to exclude other controllers and console sessions.

The result helper produces an MCP tool-result shape:

```python
def tool_result(payload, *, failed=False):
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "structuredContent": payload,
        "isError": failed,
    }
```

An adapter places this inside the JSON-RPC `result`. Here, a revision conflict is a tool failure; malformed protocol requests follow the protocol error path. [Tool results](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

## When the reply disappears

Suppose the device applies the change, but the response is lost. The controller sees a timeout. It does not yet know whether another write is justified.

```text
Controller                 Device                    Journal
    |                         |                         |
    | -- operation op-42 ---> |                         |
    |                         | apply                   |
    |        X <------------- | reply lost              |
    |                                                   |
    | -- mark outcome unknown ------------------------> |
    |                                                   |
    | -- inspect state/history -> reconcile             |
    |                                                   |
    +-- retry only after resolving the uncertainty -----+
```

I would persist the operation ID, target, authenticated subject, expected revision, and intended-change fingerprint. An idempotency key helps only when the executor can reliably associate it with the effect. A gateway log alone leaves a crash window between its database and the device.

```text
prepared --> submitted --> acknowledged --> verified
                 |
                 +--> outcome unknown --> reconcile
                                             |
                                +------------+------------+
                                |            |            |
                              applied     not applied   unresolved
```

Even reading the requested value back may not prove that this operation produced it; another writer could have applied the same value. For an audited change, that distinction matters.

For disruptive operations, I would require independent probes before confirmation. Recovery should survive the loss of the management connection it is meant to protect. These are proposed application guarantees, not guarantees provided by MCP.

## Evidence, trust, and the experiment

A resource URI identifies something; it does not make separate observations simultaneous. I would attach collection time, target identity, and relevant revision to each observation as application data.

```text
Counters at t0 -----+
                    +--> mixed-time view --> qualify the diagnosis
Routes at t1 -------+

Device text ----------------> evidence
Operator identity ----------> authorization context

"Ignore instructions" in a device banner
          |
          +--> still device data; never a permission grant
```

Resource subscriptions can signal that a host should reread state. They are not a durable event log or a global snapshot barrier. [Resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)

[Download the complete Python lab](/examples/mcp-network-lab.py) and run it with Python 3.10 or later:

```bash
python3 mcp-network-lab.py
```

It is an offline application handler with test fixtures, not an MCP transport server or authentication implementation. It uses only the standard library and never connects to equipment.

```text
Local experiment                     Result
----------------------------------   ------------------------------
Valid edit                           revision advances once
Unauthorized principal               no mutation
Stale expected revision              conflict
Malformed arguments                  rejected
Missing interface                    rejected
Caller mutates returned snapshot     stored state unchanged
Two simultaneous writers             exactly one succeeds
```

All seven tests pass. That establishes a local invariant, not fleet-scale safety or model accuracy. A next experiment should inject competing writes, dropped replies, and permission changes into equivalent CLI-shaped and typed interfaces, then measure unauthorized effects, lost updates, and unresolved outcomes—not merely task completion.

MCP makes capabilities easier to inspect across applications. The engineering question remains whether the system can explain, and enforce, exactly what an operation meant when it finally took effect.
