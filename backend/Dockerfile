FROM python:3.10.0
WORKDIR /app
COPY . ./
RUN pip install -r requirements.txt
EXPOSE 8081
ENTRYPOINT uvicorn app:app --host 0.0.0.0 --port 8081