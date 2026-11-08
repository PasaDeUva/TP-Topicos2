from fastapi import FastAPI

app = FastAPI(title="TP-Topicos2 Backend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
