from fastapi import FastAPI, HTTPException
# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
Answer the question as Biashara Plus AI assistant chatbot.(Do not state the
fact that you are Bishara Plus AI assistant everytime you answer the question).


{context}

---

Answer the question based on the above context: {question}
"""

app = FastAPI()

@app.get("/")
def root():
    return {"Biashara Plus": "AI assistant"}

@app.get("/{query_text}")
def answer_question(query_text: str) -> str:
    # if query_text == "":
    #     raise HTTPException(status_code=400, detail="Query can't be an empty string")
    # Prepare the DB.
    embedding_function = OpenAIEmbeddings()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(results) == 0 or results[0][1] < 0.7:
        return "Thank you for reaching out! I'm sorry, but I don't have the information" \
               " you need right now. You might want to contact this number [+255 679 516 178]" \
               " for further assistance."

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    model = ChatOpenAI()
    response_text = model.predict(prompt)

    # sources = [doc.metadata.get("source", None) for doc, _score in results]
    # response_with_sources = f"Response: {response_text}\nSources: {sources}"
    return response_text
