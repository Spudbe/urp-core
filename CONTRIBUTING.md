# Contributing to URP

URP is a public protocol draft. Contributions are welcome in the following forms.

## Spec Feedback

If you have feedback on the protocol design — message types, interaction flow, error codes, signing model, or anything else in SPEC.md or SPEC-v2.md — open a GitHub Issue with the label "spec".

## Bug Reports

If the reference implementation behaves incorrectly, open a GitHub Issue with the label "bug" and include the Python version, operating system, and the exact error message or unexpected output.

## Pull Requests

Small, focused pull requests are welcome. Before opening a pull request:

- Run pytest tests/ and confirm all tests pass
- Keep changes scoped to one concern per PR
- If your change affects the protocol spec, update SPEC.md in the same PR

Large architectural changes should be discussed in a GitHub Issue first.

## What This Repo Is Not

This is a protocol draft and reference implementation, not a production library. Please do not open issues requesting production features, cloud integrations, or framework support. Those belong in a separate implementation project.

## Running the Reference Implementation

Requirements: Python 3.10+

pip install -r requirements.txt
python simulations/simple_simulation.py

## License

By contributing you agree that your contributions will be licensed under the same BUSL-1.1 terms as the rest of the project. See LICENSE for details.
