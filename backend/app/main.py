from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.router import api_router

app=FastAPI(
       title="Customer Support Agent" ,description="Handling Complains"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.100.193:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return{"status":"ok","message":"Coustomer Agent is running"}
