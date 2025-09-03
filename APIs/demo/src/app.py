from fastapi import FastAPI, Request
from utils.splunk_logging import logger

app = FastAPI(title="Demo APP")

@app.get("/example/endpoint")
async def root(request: Request):
    logger.info(
        {
            "message": f"This is a demo log from the demo app",
            "X-Request-ID": request.headers.get("X-Request-ID")
        }
    )
    return {"message": "This is a demo app"}
