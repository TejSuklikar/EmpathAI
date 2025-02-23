import os
import openai
from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import BaseModel

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"Loaded api key: {OPENAI_API_KEY}")
openai.api_key = OPENAI_API_KEY

# Set up database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create FastAPI app
app = FastAPI()

# Define Chat model (table)
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default="CURRENT_TIMESTAMP")

# Ensure the table is created
Base.metadata.create_all(bind=engine)

# Pydantic model for request validation
class ChatRequest(BaseModel):
    message: str

# Dependency: Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/chat/")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Endpoint to handle chatbot messages and store conversation history.
    """
    user_input = request.message

    if not user_input:
        return {"error": "No message provided"}

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a deeply insightful and emotionally intelligent AI designed to engage in meaningful discussions. "
                    "Your goal is to help users explore their thoughts and feelings in a thoughtful, open-ended, and engaging way. "
                    "You are a compassionate conversational partner, offering reflective questions, validation, and perspective. "
                    "You focus on curiosity, introspection, and personal growth. "
                    "You do not diagnose conditions or provide medical advice, but you encourage self-awareness and thoughtful discussions."
                )
            },
            {"role": "user", "content": user_input}
        ]
    )

    ai_response = response["choices"][0]["message"]["content"]

    # Store conversation in database
    chat_entry = Chat(user_message=user_input, ai_response=ai_response)
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)

    return {"response": ai_response}

@app.get("/chats/")
async def get_chats(db: Session = Depends(get_db)):
    """
    Retrieve all chat conversations from the database.
    """
    chats = db.query(Chat).order_by(Chat.timestamp.desc()).all()
    return {
        "chats": [
            {"id": chat.id, "user_message": chat.user_message, "ai_response": chat.ai_response} 
            for chat in chats
        ]
    }
