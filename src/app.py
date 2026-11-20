from fastapi import FastAPI

from src.api.routes import router


app = FastAPI(
    title="AI Support Engine",
    description="API para analizar y clasificar solicitudes de soporte técnico.",
    version="1.0.0",
)

app.include_router(
    router,
    prefix="/api",
    tags=["Analysis"]
)


@app.get("/")
def root():
    return {
        "message": "AI Support Engine está funcionando."
    }
