from fastapi import FastAPI, HTTPException
# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Optional

from prompts import query_prompt, sys_prompt, alt_prompt

CHROMA_PATH = "chroma"

class Chat(BaseModel):
    user_message: str
    chat_history: list[tuple[str, str]]

app = FastAPI()

@app.get("/")
def root():
    return {"Biashara Plus": "AI assistant"}

@app.post("/messages")
def answer_question(chat: Chat):

    #creating the query based on the chat history
    prompt_template = ChatPromptTemplate.from_template(query_prompt)
    prompt = prompt_template.format(query=chat.user_message, chat_history=chat.chat_history)
    model = ChatOpenAI()
    query_text = model.predict(prompt)

    chat_history = chat.chat_history

    # Prepare the DB.
    embedding_function = OpenAIEmbeddings()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_relevance_scores(query_text, k=3)

    #filter unrelated and sometimes nonsensical information
    if len(results) == 0 or results[0][1] < 0.7:
        prompt_template = ChatPromptTemplate.from_template(alt_prompt)
        prompt = prompt_template.format(question=query_text, chat_history=chat_history)

        model = ChatOpenAI()
        response_text = model.predict(prompt)
        return {"data": {
            "content" : response_text
            }}

    #Preparing and giving the response
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(sys_prompt)
    prompt = prompt_template.format(context=context_text, question=query_text, chat_history=chat_history)

    model = ChatOpenAI()
    response_text = model.predict(prompt)

    return {"data": {
        "content" : response_text
        }}
