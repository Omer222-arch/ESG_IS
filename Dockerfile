FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# Install dependencies + static-files support
RUN pip install --no-cache-dir \
    uvicorn \
    fastapi \
    pydantic \
    langchain-core \
    langchain-openai \
    langgraph \
    langchain-chroma \
    chromadb \
    pandas \
    aiofiles

EXPOSE 8000

CMD ["python", "server.py"]