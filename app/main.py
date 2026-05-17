from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import embed, verify, dct

app = FastAPI()

# ✅ CORS (cho React gọi API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev thì dùng *, deploy thì đổi domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Serve file ảnh (QUAN TRỌNG)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# ✅ Routes API
app.include_router(embed.router)
app.include_router(verify.router)
app.include_router(dct.router)