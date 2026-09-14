# Fashion RAG Chatbot

A complete **Retrieval-Augmented Generation (RAG)** chatbot for an e-commerce clothing store using:

* Weaviate Vector Database
* Groq LLM API
* Semantic Search
* BM25 Keyword Search
* Hybrid Search
* Metadata Filtering
* FastAPI Chatbot API
* Docker Compose

The project demonstrates the complete lifecycle of building a production-style RAG application:

1. Deploy Weaviate locally.
2. Create database collections.
3. Import products and FAQs.
4. Test different retrieval methods.
5. Run an AI-powered chatbot using Groq.

---

## Features

* Vector search using embeddings.
* Traditional BM25 keyword search.
* Hybrid retrieval combining semantic and keyword search.
* Metadata filtering.
* FAQ retrieval.
* Product recommendation retrieval.
* LLM response generation with Groq.
* FastAPI REST API chatbot.

---

## Project Structure

```text
fashion-rag-chatbot/
│
├── docker/
│   └── docker-compose.yml
│
├── src/
│   ├── app.py
│   │
│   ├── chatbot/
│   │   └── chatbot.py
│   │
│   ├── utils/
│   │   └── utils.py
│   │
│   ├── DB/
│   │   ├── dataset/
│   │   │   ├── clothes_json.joblib
│   │   │   └── faq.joblib
│   │   │
│   │   ├── 00_intro.py
│   │   ├── 01_create_collection.py
│   │   ├── 02_import_data_products.py
│   │   ├── 03_import_data_faq.py
│   │   ├── 04_semantic_search.py
│   │   ├── 05_keyword_search.py
│   │   ├── 06_hybrid_search.py
│   │   ├── 07_filters.py
│   │   └── testing.py
│   │
│   └── .env
│
└── README.md
```

---

## System Requirements

The project was tested using:

* Ubuntu 24.04 LTS
* Docker Engine 29+
* Docker Compose v2+
* Python 3.12.x
* pip 24+
* Git

---

## Install Docker

### Remove old Docker packages

```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

### Update Ubuntu packages

```bash
sudo apt update
sudo apt upgrade -y
```

### Install required packages

```bash
sudo apt install \
ca-certificates \
curl \
gnupg \
lsb-release -y
```

### Create Docker key directory

```bash
sudo mkdir -p /etc/apt/keyrings
```

### Download Docker GPG key

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
| sudo gpg --dearmor \
-o /etc/apt/keyrings/docker.gpg
```

### Add Docker repository

```bash
echo \
"deb [arch=$(dpkg --print-architecture) \
signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### Install Docker

```bash
sudo apt update

sudo apt install \
docker-ce \
docker-ce-cli \
containerd.io \
docker-buildx-plugin \
docker-compose-plugin -y
```

### Verify installation

```bash
docker --version
docker compose version
```

### Optional

```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Clone the Repository

```bash
git clone <repository_url>

cd fashion-rag-chatbot
```

---

## Start Weaviate

Move to the docker directory:

```bash
cd docker
```

Start Weaviate:

```bash
docker compose up -d
```

Verify containers:

```bash
docker ps
```

Expected result:

```text
weaviate
text2vec-transformers
```

---

## Stop Weaviate

```bash
docker compose down
```

Remove volumes for a clean database:

```bash
docker compose down -v
```

---

## Create Virtual Environment

Return to the project root:

```bash
cd ..
```

Create the environment:

```bash
python3.12 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Expected terminal prefix:

```text
(venv)
```

---

## Install Dependencies

Move to source directory:

```bash
cd src
```

Upgrade pip:

```bash
pip install --upgrade pip
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create or edit:

```text
src/.env
```

Example:

```env
GROQ_API_KEY=your_groq_api_key
WEAVIATE_HOST=localhost
WEAVIATE_PORT=8080
```

Replace `your_groq_api_key` with your Groq API key.

---

## Verify Weaviate Connection

```bash
cd DB

python 00_intro.py
```

Expected output:

```text
Weaviate client version: x.x.x
Connection successful: True
```

---

## Create Database Schema

```bash
python 01_create_collection.py
```

Example collections:

* Products
* FAQ

If collections already exist:

```bash
docker compose down -v
docker compose up -d
```

Then recreate them.

---

## Import Products Dataset

```bash
python 02_import_data_products.py
```

Dataset location:

```text
src/DB/dataset/clothes_json.joblib
```

---

## Import FAQ Dataset

```bash
python 03_import_data_faq.py
```

Dataset location:

```text
src/DB/dataset/faq.joblib
```

---

## Test Semantic Search

```bash
python 04_semantic_search.py
```

Example query:

```text
I need a gray shirt for casual wear
```

---

## Test BM25 Keyword Search

```bash
python 05_keyword_search.py
```

Example query:

```text
gray shirt
```

---

## Test Hybrid Search

```bash
python 06_hybrid_search.py
```

Hybrid search combines:

* Vector similarity
* BM25 ranking

---

## Test Metadata Filters

```bash
python 07_filters.py
```

Examples:

* Category = Men
* Color = Gray
* Brand = Adidas
* Price < 50

---

## General Retrieval Testing

```bash
python testing.py
```

Useful for:

* Retrieval evaluation
* Method comparison
* Prompt experimentation
* Search debugging

---

## Running the Chatbot API

Move back to source directory:

```bash
cd ..
```

Run FastAPI:

```bash
uvicorn app:app --reload
```

Expected output:

```text
INFO: Uvicorn running on http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

## Example API Request

```bash
curl -X POST http://localhost:8000/chat \
-H "Content-Type: application/json" \
-d '{
    "message": "I need a gray t-shirt"
}'
```

Example response:

```json
{
    "response": "We have several gray t-shirts available including Adidas and Mr.Men options."
}
```

---

## Typical Workflow

### First Run

```bash
docker compose up -d

python 00_intro.py

python 01_create_collection.py

python 02_import_data_products.py

python 03_import_data_faq.py

uvicorn app:app --reload
```

### Development Workflow

```bash
docker compose up -d

uvicorn app:app --reload
```

### Reset Everything

```bash
docker compose down -v

docker compose up -d

python 01_create_collection.py

python 02_import_data_products.py

python 03_import_data_faq.py
```

---

## Retrieval Pipeline

```text
User Question
      ↓
Query Understanding
      ↓
Weaviate Retrieval
 ├── Semantic Search
 ├── BM25 Search
 ├── Hybrid Search
 └── Filtering
      ↓
Context Construction
      ↓
Groq LLM
      ↓
Final Response
```

---

## Future Improvements

* Cross Encoder Re-ranking
* Query Expansion
* Multi-turn Memory
* Product Recommendation Engine
* Streaming Responses
* User Authentication
* Conversation History Storage
* Observability and Monitoring

---

## Technologies Used

* Python 3.12
* FastAPI
* Uvicorn
* Weaviate
* Groq
* Docker
* Pandas
* Joblib

---

## License

This project is intended for educational purposes and experimentation with modern RAG systems and vector databases.
