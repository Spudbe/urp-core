"""TRP command-line interface.

Usage:
    trp verify <receipt.json>          Verify a ToolReceipt by replaying registered tools
    trp match <claim.json> <evidence>  Match a StructuredClaim against receipt evidence
    trp hash <file.json>               Compute JCS canonical hash of a JSON file
    trp version                        Print TRP version
"""

import argparse
import json
import os
import sys

from trp import __version__
from trp.canonical import sha256_hex
from trp.core import ToolReceipt
from trp.deterministic_tools import BUILTIN_TOOLS
from trp.verify import ToolReceiptVerifier, VerificationStatus
from trp.structured_claim import StructuredClaim
from trp.claim_verifier import match_claim


def _build_verifier() -> ToolReceiptVerifier:
    v = ToolReceiptVerifier()
    for name, fn in BUILTIN_TOOLS.items():
        v.register(name, fn)
    return v


def cmd_verify(args):
    """Verify a ToolReceipt JSON file."""
    with open(args.receipt, "r") as f:
        data = json.load(f)
    receipt = ToolReceipt.from_dict(data)
    verifier = _build_verifier()
    result = verifier.verify(receipt)
    output = result.to_dict()
    print(json.dumps(output, indent=2))
    sys.exit(0 if result.status == VerificationStatus.VERIFIED_EXACT else 1)


def cmd_match(args):
    """Match a StructuredClaim against evidence files."""
    with open(args.claim, "r") as f:
        sc_data = json.load(f)
    sc = StructuredClaim.from_dict(sc_data)

    receipts = []
    evidence_path = args.evidence
    if os.path.isfile(evidence_path):
        with open(evidence_path, "r") as f:
            receipts.append(ToolReceipt.from_dict(json.load(f)))
    elif os.path.isdir(evidence_path):
        for fname in sorted(os.listdir(evidence_path)):
            if fname.endswith(".json"):
                fpath = os.path.join(evidence_path, fname)
                try:
                    with open(fpath, "r") as f:
                        receipts.append(ToolReceipt.from_dict(json.load(f)))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

    result = match_claim(sc, receipts)
    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0 if result.overall_status.value == "true" else 1)


def cmd_hash(args):
    """Compute JCS canonical hash of a JSON file."""
    with open(args.file, "r") as f:
        data = json.load(f)
    print(sha256_hex(data))
    sys.exit(0)


def cmd_version(args):
    """Print TRP version."""
    print(f"trp-core {__version__}")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="trp",
        description="TRP — Tool Receipt Protocol CLI",
    )
    sub = parser.add_subparsers(dest="command")

    p_verify = sub.add_parser("verify", help="Verify a ToolReceipt JSON file")
    p_verify.add_argument("receipt", help="Path to receipt JSON file")
    p_verify.set_defaults(func=cmd_verify)

    p_match = sub.add_parser("match", help="Match a StructuredClaim against evidence")
    p_match.add_argument("claim", help="Path to StructuredClaim JSON file")
    p_match.add_argument("evidence", help="Path to receipt JSON file or directory of receipts")
    p_match.set_defaults(func=cmd_match)

    p_hash = sub.add_parser("hash", help="Compute JCS canonical hash of a JSON file")
    p_hash.add_argument("file", help="Path to JSON file")
    p_hash.set_defaults(func=cmd_hash)

    p_version = sub.add_parser("version", help="Print TRP version")
    p_version.set_defaults(func=cmd_version)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
