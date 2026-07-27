# HealthPlusAi-
"HealthPlus AI is an AI chatbot for hospitals. Instead of answering from the internet, it answers only using hospital documents like SOPs, doctor details, pricing, FAQs, and policies. It uses RAG, vector search, and LLMs to provide accurate answers with citations."
# 🏥 HealthPlus AI

An AI-powered Hospital Operations Assistant built using **Retrieval-Augmented Generation (RAG)**. The application enables hospital staff and patients to ask questions about hospital documents such as SOPs, doctor information, pricing, policies, FAQs, and health packages, and receive accurate, source-cited answers using Large Language Models.

> ⚠️ **Disclaimer:** All hospital documents used in this project are fictional and created for educational purposes. This application is **not intended for clinical diagnosis or medical treatment.**

---

# 🚀 Features

- 📄 Upload and process hospital PDF documents
- 🤖 AI-powered chatbot using Claude/OpenAI
- 🔍 Semantic search using Vector Database
- 📚 Retrieval-Augmented Generation (RAG)
- 📌 Source citations for every response
- ⚡ Real-time streaming responses
- 🧠 Conversation memory
- 🔄 Switch between Claude and ChatGPT
- 🛡️ Guardrails to prevent hallucinations
- 🏥 Hospital-focused knowledge base

---

# 🏗️ System Architecture

```
                   User
                     │
                     ▼
             Streamlit Web UI
                     │
                     ▼
              Chat Service
                     │
        Query Processing & Memory
                     │
                     ▼
           Semantic Retrieval
                     │
                     ▼
              ChromaDB Vector DB
                     │
                     ▼
          Retrieved Document Chunks
                     │
                     ▼
          Claude / OpenAI API
                     │
                     ▼
         Response with Citations
```

---

# 📂 Knowledge Base

The chatbot can retrieve information from hospital documents such as:

- Standard Operating Procedures (SOPs)
- Doctor Information
- Pricing Catalog
- Diagnostic Tests
- Health Packages
- Policies
- Frequently Asked Questions
- Hospital Reports

---

# ⚙️ Tech Stack

### Programming Language

- Python

### AI / Machine Learning

- Retrieval-Augmented Generation (RAG)
- Large Language Models (Claude/OpenAI)
- Sentence Transformers

### Vector Database

- ChromaDB

### Embedding Model

- BAAI BGE Small

### Backend

- FastAPI

### Frontend

- Streamlit

### Document Processing

- PyMuPDF
- LangChain Text Splitters

### Database

- ChromaDB Vector Store

### Cloud

- Google Cloud
- AWS

### Tools

- Git
- GitHub
- Docker

---

# 📁 Project Structure

```
HealthPlus-AI/
│
├── src/
│   ├── application/
│   ├── presentation/
│   ├── llm/
│   ├── vector_database/
│   ├── knowledge_base/
│   ├── document_pipeline/
│   └── config/
│
├── scripts/
├── tests/
├── data/
├── docs/
├── logs/
├── README.md
└── pyproject.toml
```

---

# 🔄 Workflow

1. Upload hospital PDF documents.
2. Extract text from PDFs.
3. Clean and preprocess text.
4. Split documents into chunks.
5. Generate embeddings.
6. Store embeddings in ChromaDB.
7. User asks a question.
8. Perform semantic similarity search.
9. Retrieve relevant document chunks.
10. Send retrieved context to the LLM.
11. Generate an accurate response with citations.

---

# 💡 Example Questions

- What is the MRI scan cost?
- Who is the cardiologist?
- What are the visiting hours?
- What is the refund policy?
- Which doctor specializes in orthopedics?
- What health packages are available?
- How do I book an appointment?

---

# 📸 Screenshots

Add screenshots of your application here.

Example:

```
docs/screenshots/home.png
docs/screenshots/chat.png
docs/screenshots/upload.png
```

---

# ▶️ Installation

Clone the repository

```bash
git clone https://github.com/DavidJain/health-plus-ai.git
```

Move into the project

```bash
cd health-plus-ai
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate the environment

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file.

```
ANTHROPIC_API_KEY=YOUR_API_KEY

OPENAI_API_KEY=YOUR_API_KEY
```

---

# ▶️ Run the Application

```bash
streamlit run src/healthplus/presentation/app.py
```

---

# 📈 Future Improvements

- Voice-enabled chatbot
- Appointment booking integration
- OCR support for scanned PDFs
- Multi-language support
- Authentication system
- Cloud deployment
- Admin dashboard
- Analytics dashboard

---

# 👨‍💻 Author

**David Jain**

LinkedIn

https://www.linkedin.com/in/jain-david-8541ba320

GitHub

https://github.com/DavidJain

LeetCode

https://leetcode.com/u/23BCE9446v/

---

# ⭐ If you found this project useful, consider giving it a star!
