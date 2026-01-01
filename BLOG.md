# Building meta-threads: a quick dev log

_Date: 2026-01-01_

I wanted a minimal Python wrapper around Meta’s Threads API, so I sketched out a quick scaffold with modern packaging and a small HTTP client.

## Picking the name
- Landed on `meta-threads` to stay descriptive, PyPI-friendly, and avoid name collisions.

## Packaging setup
- Chose Hatchling for lightweight builds and a clean `pyproject.toml`.
- Targeted Python 3.9+ and added `httpx` as the sole runtime dependency.
- Added project metadata (version, description, URLs) and wired the wheel target to `src/meta_threads`.

## Layout
- Kept a simple `src/` structure with `meta_threads` as the package root.
- Added `__init__.py` to expose the public interface and a single `client.py` for now.

## Client scaffold
- Wrapped `httpx.Client` with a tiny `ThreadsClient` that injects a bearer token and base URL.
- Implemented a shared `_request` helper that raises on non-2xx responses.
- Stubbed two example calls: `get_user(user_id)` and `create_thread(text, media_id=None)`.
- Included context manager support so you can use `with ThreadsClient(...) as client:` to ensure cleanup.

## README and tests
- Wrote a short README with install and usage examples.
- Added `tests/test_basic.py` to assert the client instantiates and preserves the base URL; it’s a placeholder for real HTTP tests.

## Next steps
- Flesh out endpoint coverage following the official Threads docs (media upload, replies, pagination, errors).
- Add typed response models and richer error handling instead of raw dicts.
- Provide async support via `httpx.AsyncClient`.
- Publish to PyPI once the API surface and tests are solid.

## Publishing
- Bumped version to 0.1.1 and added project URLs in `pyproject.toml`.
- Built artifacts via `python -m build` and validated with `python.exe -m twine check dist/*`.
- Uploaded to TestPyPI with `python.exe -m twine upload --repository-url https://test.pypi.org/legacy/ dist/threads_py-0.1.1*` using a TestPyPI token.
- Next: upload to PyPI with the same artifacts and a fresh PyPI token.
