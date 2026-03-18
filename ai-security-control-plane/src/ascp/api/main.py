"""Run operator API: ``ascp-serve`` or ``python -m ascp.api.main``."""

from __future__ import annotations


def main() -> None:
    import sys

    try:
        import uvicorn
    except ImportError as e:
        print(
            "The operator API requires optional dependencies. Install with:\n"
            "  pip install 'ascp[api]'",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    from ascp.config import Settings

    s = Settings()
    uvicorn.run(
        "ascp.api.app:app",
        host="0.0.0.0",
        port=8000,
        log_level=s.log_level.lower(),
    )


if __name__ == "__main__":
    main()
