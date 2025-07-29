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
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the claim."
    },
    "statement": {
      "type": "string",
      "minLength": 1,
      "description": "The propositional content of the claim."
    },
    "type": {
      "type": "string",
      "enum": ["assertion", "request"],
      "description": "Whether this is an assertion of fact or a request for data/action."
    },
    "proof_ref": {
      "$ref": "#/$defs/ProofReference"
    },
    "stake": {
      "$ref": "#/$defs/Stake"
    }
  },
  "additionalProperties": false,
  "$defs": {
    "ProofReference": {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "type": "object",
      "required": ["hash", "location", "summary"],
      "properties": {
        "hash": {
          "type": "string",
          "description": "Cryptographic hash of the proof data (e.g. SHA-256)."
        },
        "location": {
          "type": "string",
          "format": "uri",
          "description": "URI where the proof can be retrieved (e.g. IPFS link)."
        },
        "summary": {
          "type": "string",
          "description": "Short human-readable summary of the proof contents."
        }
      },
      "additionalProperties": false
    },
    "Stake": {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "type": "object",
      "required": ["amount", "currency", "refundable"],
      "properties": {
        "amount": {
          "type": "number",
          "minimum": 0,
          "description": "Quantity of URP credits locked with the claim."
        },
        "currency": {
          "type": "string",
          "pattern": "^[A-Z]{3,5}$",
          "description": "Unit of account (e.g. ‘URC’)."
        },
        "refundable": {
          "type": "boolean",
          "description": "Whether the stake is returned on acceptance."
        }
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
      "stake": {
        "amount": 0.5,
        "currency": "URC",
        "refundable": true
      }
    }
  ]
}
