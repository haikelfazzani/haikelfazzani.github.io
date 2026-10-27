---
title: "Beyond the Swarm API: Why We Need an Agent Network Protocol (ANP)"
description: "Exploring why centralized orchestration limits agent networks and introducing the Agent Network Protocol (ANP) for decentralized, scalable multi-agent systems."
publishedDate: 2025-09-30
---

By Haikel Fazzani

We've spent the last few years obsessed with prompt templates, function calling, and local memory vectors. We built autonomous script loops, wrapped LLM calls in REST endpoints, and declared that "multi-agent systems" had finally arrived.

Except they haven't. Not at scale.

What we actually built are centralized orchestrators pretending to be agent networks. If your system breaks the moment a primary controller goes down, or if adding a new autonomous worker requires updating a centralized Python router graph, you haven't built a network—you've built a monolithic microservice with high inference costs.

If distributed AI is ever going to scale across organizations, cloud providers, and local edge hardware, we need lower-level primitives. We need a native protocol for decentralized agent routing and dynamic discovery.

Enter the Agent Network Protocol (ANP).

## The Core Bottleneck: Centralized Orchestration vs. Network Discovery

In standard agentic frameworks (like LangGraph, AutoGen, or CrewAI), execution and routing are tightly coupled. Everything relies on a central node that holds the map of who can do what.

```
+-------------------------------------------------------------+
|               TRADITIONAL AGENT ORCHESTRATION               |
|                                                             |
|                   [ Central Coordinator ]                   |
|                  /           |           \                  |
|                 v            v            v                 |
|            [Agent A]     [Agent B]    [Agent C]             |
|          (Local Task)   (Database)   (Third-arty)          |
+-------------------------------------------------------------+
```

This design works well when all nodes live inside the same process or VPC. But real-world deployment looks messy:

- Agent A runs inside an enterprise financial database behind strict firewalls.
- Agent B is a local edge node running a quantized Llama model on user hardware.
- Agent C is a paid third-party execution API with zero-trust requirements.

You cannot run all three inside a single monolithic loop. Instead of hardcoded routing tables, agents need peer-to-peer discovery, network-level routing, capability verification, and asynchronous handshake negotiation without a single point of failure.

## The ANP Architecture

ANP operates below the model tier. It does not dictate how an LLM thinks; it defines how nodes discover each other, verify identities, and exchange tasks.

```
+-------------------------------------------------------------+
|                      ANP NETWORK MESH                       |
|                                                             |
|    [Node A] <====== DHT / Peer Discovery ======> [Node B]   |
|       ||                                            ||      |
|       ||============ Signed ANP Packet =============||      |
+-------------------------------------------------------------+
```

### 1. Peer Discovery & Dynamic Capabilities

Instead of publishing rigid OpenAPI specs or importing static tool definitions, ANP nodes advertise Capability Cards across a Distributed Hash Table (DHT) or peer mesh.

A capability card combines deterministic JSON-schema constraints with semantic embeddings to describe what a node can handle:

```json
{
  "anp_version": "1.0.0-alpha",
  "node_id": "anp:peer:12D3KooWEvG9qXz8...",
  "capabilities": [
    {
      "intent": "code.refactor.javascript",
      "context_window_max": 128000,
      "latency_p95_ms": 350,
      "verification": "zk-proof-v1"
    }
  ],
  "transport": {
    "protocol": "libp2p/noise",
    "multiaddr": "/ip4/192.168.1.50/tcp/9000/p2p/12D3Koo..."
  }
}
```

### 2. Intent-Based Routing

Traditional IP networks route traffic based on destination addresses. ANP routes traffic based on Intent and SLA Constraints.

When an agent needs a task executed:

- **Intent Generation**: Node A generates a query describing the target action (code.refactor.javascript) along with constraints (max latency, cost budget, privacy tier).
- **Peer Matching**: Nearby nodes in the network evaluate whether they satisfy the criteria without needing a central index.
- **Dispatch**: The request routes directly to the optimal peer based on network topology and cryptographic reputation.

## Anatomy of an ANP Session

ANP relies on lightweight binary transport protocols layered over QUIC or WebSockets rather than verbose HTTP REST payloads.

```
  Origin Node                                Target Peer
      |                                           |
      | ------ 1. ANP_SYN (Intent + Proof) -----> |
      |                                           |
      | <----- 2. ANP_ACK (SLA + Session Key) --- |
      |                                           |
      | ------ 3. ANP_EXEC (Encrypted State) ---> |
      |                                           |
      | <----- 4. ANP_STREAM (Token Stream) ----- |
      v                                           v
```

### Sequence Flow

- **ANP_SYN**: The initiating node broadcasts an execution request containing intent specifications, context parameters, and cryptographic auth credentials.
- **ANP_ACK**: The target peer evaluates its current load and capabilities, accepts the SLA, and returns an ephemeral public key for session encryption.
- **ANP_EXEC**: The origin node sends the actual encrypted state payload.
- **ANP_STREAM**: Results stream back asynchronously over a secure socket connection as tokens, tool calls, or state updates.

## Practical Node Implementation (Node.js)

Below is a lightweight JavaScript/Node.js conceptual implementation showing how an ANP peer registers capabilities and processes incoming intent packets:

```javascript
import { EventEmitter } from 'node:events';

class AnpNode extends EventEmitter {
  constructor(peerId) {
    super();
    this.peerId = peerId;
    this.capabilities = new Map();

    // Register a local execution capability
    this.capabilities.set('code.refactor.javascript', {
      maxTokens: 128000,
      handler: async (payload) => {
        return { status: 'success', refactoredCode: '// Optimized code' };
      }
    });
  }

  // Handle incoming encrypted or signed ANP packet
  async handleIncomingPacket(packet) {
    const { senderId, intent, payload } = packet;

    console.log(`[ANP] Received packet from: ${senderId} for intent: ${intent}`);

    const capability = this.capabilities.get(intent);
    if (!capability) {
      throw new Error(`[ANP] Unhandled intent: ${intent}`);
    }

    // Execute task handler if network constraints are met
    const result = await capability.handler(payload);
    return {
      senderId: this.peerId,
      targetId: senderId,
      intentResponse: intent,
      data: result
    };
  }
}

// Example usage
const node = new AnpNode('anp:peer:8x92f1a...');

const incomingPacket = {
  senderId: 'anp:peer:3k12b9z...',
  intent: 'code.refactor.javascript',
  payload: { source: 'function test() { return 1; }' }
};

node.handleIncomingPacket(incomingPacket)
  .then(response => console.log('[ANP] Response payload:', response))
  .catch(err => console.error('[ANP] Execution failed:', err.message));
```

## Why This Matters Now

As single-purpose autonomous models proliferate across cloud providers, private enterprise servers, and consumer devices, integration friction becomes the primary bottleneck.

If connecting two autonomous agents requires custom REST endpoints, explicit API key exchanges, and centralized orchestration logic, the ecosystem will fragment.

By shifting discovery, capability negotiation, and routing down to a dedicated network layer, ANP enables:

- **Zero-Trust Autonomous Execution**: Agents interact securely without requiring mutual platform ownership.
- **Decentralized Topologies**: Eliminates single points of failure and central coordinator bottlenecks.
- **Dynamic Compute Allocation**: Nodes join the mesh, offer specialized capabilities or compute capacity, execute workloads, and disconnect seamlessly.

## Get In Touch

ANP is an open design effort focused on building resilient transport and routing primitives for autonomous software.

If you are researching distributed systems, peer-to-peer networking, or agent infrastructure, feel free to collaborate or reach out:

- **GitHub**: haikelfazzani
- **Email**: haikel.fazzani@gmail.com
