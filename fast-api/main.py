from typing import Union
from fastapi import FastAPI
from yandex_assistant import Assistant
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
assistant = Assistant()

origins = [
    "http://localhost",
    "https://localhost",
    "http://localhost:8080",
    "http://localhost:3000",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    query: str


@app.get("/")
def read_root():   
    return {"status": "OK"}


@app.post("/ask")
async def ask_question(request: Question):
    try:
        response = assistant.ask(request.query)
        return response
    except Exception as e:
        print(f'{e}')
        return {'error': str(e)}
    


@app.on_event("shutdown")
def shutdown_event():
    assistant.shutdown()
