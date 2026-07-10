# backend/api-gateway/src/main.py
# -------------------------------------------------------------------------
# Composition root bootstraps the modular routers and configures middlewares
# -------------------------------------------------------------------------

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import db_manager
from .routers.alerts import router as alerts_router
from .routers.auth import router as auth_router
from .routers.bins import router as bins_router

# Configure root logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("APIGateway")

app = FastAPI(title="Smart Waste Bin IoT API Gateway")

# Initialize database pool and startup seeder cleanly
db_manager.initialize()

# Configure CORS Middleware safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers
app.include_router(auth_router)
app.include_router(bins_router)
app.include_router(alerts_router)
