import uvicorn

from finops_token_saver.infrastructure.bootstrap import create_configured_app

app = create_configured_app()


def run() -> None:
    uvicorn.run("finops_token_saver.main:app", host="0.0.0.0", port=8000, reload=False)
