FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p static
EXPOSE 8080
CMD ["python", "-c", "import os; import uvicorn; uvicorn.run('server:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))"]
