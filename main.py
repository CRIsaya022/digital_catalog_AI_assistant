from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from prompts import query_prompt, sys_prompt, alt_prompt

import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["biashara"]
user_messages_collection = db["user_messages"]

CHROMA_PATH = "chroma"

class Chat(BaseModel):
    user_message: str
    user_id: str
class User(BaseModel):
    user_id: str

app = FastAPI()

@app.get("/")
def root():
    return {"Biashara Plus": "AI assistant"}

@app.post("/answer_query")
def answer_question(chat: Chat):
    # Fetch or create chat history for the user
    user_data = user_messages_collection.find_one({"user_id": chat.user_id})
    if not user_data:
        user_data = {"user_id": chat.user_id, "messages": []}
        user_messages_collection.insert_one(user_data)

    chat_history = user_data["messages"]

    # Add the current message to chat history
    chat_history.append(("user", chat.user_message))

    # Update the user's chat history in the database
    user_messages_collection.update_one(
        {"user_id": chat.user_id},
        {"$set": {"messages": chat_history}}
    )

    # Create the query based on the chat history
    prompt_template = ChatPromptTemplate.from_template(query_prompt)
    prompt = prompt_template.format(query=chat.user_message, chat_history=chat_history[-9:])
    model = ChatOpenAI()
    query_text = model.predict(prompt)

    # Prepare the db for similarity search
    embedding_function = OpenAIEmbeddings()
    data_base = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the db
    results = data_base.similarity_search_with_relevance_scores(query_text, k=3)

    # edge case for nonsesical or irrelevant information
    if len(results) == 0 or results[0][1] < 0.7:
        prompt_template = ChatPromptTemplate.from_template(alt_prompt)
        prompt = prompt_template.format(question=query_text, chat_history=chat_history[-9:])

        response_text = model.predict(prompt)

        chat_history.append(("bot", response_text))
        user_messages_collection.update_one(
        {"user_id": chat.user_id},
        {"$set": {"messages": chat_history}})

        return {"data": {"content": response_text}}

    # Prepare and give the response
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(sys_prompt)
    prompt = prompt_template.format(context=context_text, question=query_text, chat_history=chat_history[-9:])

    response_text = model.predict(prompt)

    # Update the chat history with the bot's response
    chat_history.append(("bot", response_text))
    user_messages_collection.update_one(
        {"user_id": chat.user_id},
        {"$set": {"messages": chat_history}}
    )

    return {"data": {"content": response_text}}

@app.post("/load_conversation")
def get_messages(customer: User):
    user_id = customer.user_id
    # Fetch or create chat history for the user
    user_data = user_messages_collection.find_one({"user_id": user_id})
    if not user_data:
        user_data = {"user_id": user_id, "messages": [("bot", "Hello! I am Beatha, your AI customer assistant for Biashara Plus. How can I help you today?")]}
        user_messages_collection.insert_one(user_data)

    chat_history = user_data["messages"]
    return {"data": {"content": chat_history}}