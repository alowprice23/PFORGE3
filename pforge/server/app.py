from fastapi import FastAPI
from pforge.server.routes import healthz, metrics

app = FastAPI()

app.include_router(healthz.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")

@app.get("/")
def read_root():
    return {"Hello": "World"}
