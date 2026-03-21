````markdown
# Universal Reasoning Protocol – Detailed Specification (v2)

## 1. Introduction
- Purpose, goals and non‑goals  
- Overview of agents & message flow

## 2. Core Message Types & JSON Schemas

### 2.1 Claim
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "URP Claim",
  "description": "An atomic assertion of fact or intent, with attached proof reference and stake.",
  "type": "object",
  "required": ["id", "statement", "type", "proof_ref", "stake"],
  "properties": {
    "id": { "type": "string", "format": "uuid", "description": "Unique identifier for the claim." },
    "statement": { "type": "string", "minLength": 1, "description": "The propositional content of the claim." },
    "type": { "type": "string", "enum": ["assertion", "request"], "description": "Whether this is an assertion of fact or a request for data/action." },
    "proof_ref": { "$ref": "#/$defs/ProofReference" },
    "stake": { "$ref": "#/$defs/Stake" }
  },
  "additionalProperties": false,
  "$defs": {
    "ProofReference": {
      "type": "object",
      "required": ["hash", "location", "summary"],
      "properties": {
        "hash": { "type": "string", "description": "Cryptographic hash of the proof data (e.g. SHA‑256)." },
        "location": { "type": "string", "format": "uri", "description": "URI where the proof can be retrieved (e.g. IPFS link)." },
        "summary": { "type": "string", "description": "Short human‑readable summary of the proof contents." },
        "confidence_score": { "type": "number", "minimum": 0, "maximum": 1, "description": "Submitting agent's confidence in the evidence (0.0 = speculative, 1.0 = certain). Optional." }
      },
      "additionalProperties": false
    },
    "Stake": {
      "type": "object",
      "required": ["amount", "currency", "refundable"],
      "properties": {
        "amount": { "type": "number", "minimum": 0, "description": "Quantity of URP credits locked with the claim." },
        "currency": { "type": "string", "pattern": "^[A-Z]{3,5}$", "description": "Unit of account (e.g. 'URC')." },
        "refundable": { "type": "boolean", "description": "Whether the stake is returned on acceptance." }
      },
      "additionalProperties": false
    }
  },
  "examples": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "statement": "What is the boiling point of water at sea level?",
      "type": "assertion",
      "proof_ref": {
        "hash": "3a7bd3e2360a58c6bb89e7b5f3a6412cd8e4f3f1b0f4f5b6c7a8d9e0f1a2b3c4",
        "location": "ipfs://QmExampleHash",
        "summary": "Exactly 100°C at standard pressure."
      },
      "stake": { "amount": 0.5, "currency": "URC", "refundable": true }
    }
  ]
}
```

### 2.2 ProofReference
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "#ProofReference",
  "title": "URP ProofReference",
  "description": "Pointer to an external proof artifact.",
  "type": "object",
  "required": ["hash", "location", "summary"],
  "properties": {
    "hash": { "type": "string", "description": "Cryptographic hash of the proof data (e.g. SHA‑256)." },
    "location": { "type": "string", "format": "uri", "description": "URI where the proof can be retrieved (e.g. IPFS link)." },
    "summary": { "type": "string", "description": "Short human‑readable summary of the proof contents." },
    "confidence_score": { "type": "number", "minimum": 0, "maximum": 1, "description": "Submitting agent's confidence in the evidence (0.0 = speculative, 1.0 = certain). Optional." }
  },
  "additionalProperties": false
}
```

### 2.3 Stake
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "#Stake",
  "title": "URP Stake",
  "description": "Stake attached to signal confidence and fund verification.",
  "type": "object",
  "required": ["amount", "currency", "refundable"],
  "properties": {
    "amount": { "type": "number", "minimum": 0, "description": "Quantity of URP credits locked with the claim." },
    "currency": { "type": "string", "pattern": "^[A-Z]{3,5}$", "description": "Unit of account (e.g. 'URC')." },
    "refundable": { "type": "boolean", "description": "Whether the stake is returned on acceptance." }
  },
  "additionalProperties": false
}
```

### 2.4 Response
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "URP Response",
  "description": "Decision on a claim, optionally including a counter‑stake or proof.",
  "type": "object",
  "required": ["claim_id", "decision"],
  "properties": {
    "claim_id": { "type": "string", "format": "uuid", "description": "Identifier of the claim being responded to." },
    "decision": { "type": "string", "enum": ["accept", "reject", "challenge"], "description": "Decision on the claim." },
    "proof_ref": {
      "anyOf": [ { "$ref": "#/$defs/ProofReference" }, { "type": "null" } ],
      "description": "Optional proof supporting the decision."
    },
    "stake": {
      "anyOf": [ { "$ref": "#/$defs/Stake" }, { "type": "null" } ],
      "description": "Optional stake for challenges."
    }
  },
  "additionalProperties": false,
  "$defs": {
    "ProofReference": {
      "type": "object",
      "required": ["hash", "location", "summary"],
      "properties": {
        "hash": { "type": "string" },
        "location": { "type": "string", "format": "uri" },
        "summary": { "type": "string" },
        "confidence_score": { "type": "number", "minimum": 0, "maximum": 1, "description": "Submitting agent's confidence in the evidence (0.0 = speculative, 1.0 = certain). Optional." }
      },
      "additionalProperties": false
    },
    "Stake": {
      "type": "object",
      "required": ["amount", "currency", "refundable"],
      "properties": {
        "amount": { "type": "number", "minimum": 0 },
        "currency": { "type": "string", "pattern": "^[A-Z]{3,5}$" },
        "refundable": { "type": "boolean" }
      },
      "additionalProperties": false
    }
  }
}
```

## 3. Out of Scope for v0.2

The following topics are recognised as necessary for a complete protocol but are deferred to future versions: proof serialisation format, transport protocol bindings, agent identity and signing model, privacy and encryption, governance and versioning, and microtransaction/settlement layer. See ROADMAP.md for planned work.
````
