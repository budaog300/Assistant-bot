from typing import Union
from fastapi import FastAPI
from yandex_assistant import Assistant
from pydantic import BaseModel

app = FastAPI()
assistant = Assistant()


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
