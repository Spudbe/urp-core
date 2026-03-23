# Contributing to TRP

TRP is Apache-2.0 licensed. Contributions welcome.

## Setup

```bash
git clone https://github.com/Spudbe/trp-core.git
cd trp-core
pip install -r requirements.txt
pip install pytest httpx
python -m pytest tests/ -q  # should pass 300+ tests
```

## Adding a deterministic tool

1. Add your function to `trp/deterministic_tools.py`:
```python
def my_tool(inputs: dict) -> dict:
    """Must be pure — same inputs always produce same outputs."""
    result = do_something(inputs["param"])
    return {"result": result}
```

2. Register it in `BUILTIN_TOOLS`:
```python
BUILTIN_TOOLS = {
    ...,
    "my_tool": my_tool,
}
```

3. Add tests in `tests/test_verify.py` with pinned hash vectors.

## Adding a StructuredClaim proposition type

1. Add the dataclass to `trp/structured_claim.py` (frozen, with `to_dict` and `from_dict`)
2. Add it to the `proposition_from_dict` factory
3. Add matching logic to `trp/claim_verifier.py`
4. Add tests covering serialisation, matching, and three-valued logic

## Code conventions

- All protocol types use `to_dict()` / `from_dict()` for serialisation
- All hashing uses `trp/canonical.py` (RFC 8785 JCS)
- Tests go in `tests/test_<module>.py`
- Commit messages: `feat:`, `fix:`, `docs:`, `spec:`, `chore:`

## Running tests

```bash
python -m pytest tests/ -q        # quick
python -m pytest tests/ -v        # verbose
python -m pytest tests/test_verify.py  # single module
```
