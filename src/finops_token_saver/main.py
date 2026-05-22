import uvicorn

from finops_token_saver.api.app import create_app

app = create_app()


def run() -> None:
    uvicorn.run("finops_token_saver.main:app", host="0.0.0.0", port=8000, reload=False)
