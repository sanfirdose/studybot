import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate 
from pymongo import MongoClient
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
mongo_uri = os.getenv("MONGO_URI")

client = MongoClient(mongo_uri)
db=client["studybuddy"]
collection=db["users"]

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    question: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a study buddy. You help students with their questions and provide explanations in a friendly and supportive manner. Always encourage the student to ask more questions if they need further clarification."),
    ("placeholder","{history}"),
    ("human", "{input}")
])

llm = ChatGroq(api_key=groq_api_key, model="openai/gpt-oss-20b")
chain = prompt | llm

user_id = "user123"

def get_history(user_id):
    chats = collection.find({"user_id": user_id}).sort("timestamp", 1)
    history=[]
    for chat in chats:
        history.append({"role": chat["role"], "content": chat["message"]})
    return history

@app.get("/")
def home():
    return {"message": "Welcome to Study Buddy!"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>
            <rect width='100%' height='100%' fill='#4F46E5'/>
            <text x='50%' y='50%' fill='white' dominant-baseline='middle' text-anchor='middle' font-size='10'>SB</text>
        </svg>
        """
        return Response(content=svg, media_type="image/svg+xml")

@app.post("/chat")
def chat(request: ChatRequest): 
    history = get_history(request.user_id)
    response = chain.invoke({"history": history, "input": request.question})

    collection.insert_one({
        "user_id": request.user_id, 
        "message": request.question,
        "role": "user", 
        "timestamp": datetime.utcnow()})
    
    collection.insert_one({
        "user_id": request.user_id,
        "message": response.content,
        "role": "assistant",
        "timestamp": datetime.utcnow()})

    return {"response": response.content}

