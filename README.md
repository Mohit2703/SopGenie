# 📚 SOP RAG - AI-Powered Document Q&A System
Transform your Standard Operating Procedures and technical documents into an intelligent, conversational knowledge base using Retrieval Augmented Generation (RAG).

## 🌟 Features
* **🤖 AI-Powered Q&A**: Chat with your documents using RAG technology powered by Mistral AI
* **💬 Conversational Interface**: Perplexity-style chat sessions with context-aware responses
* **👥 Team Collaboration**: Multi-user support with role-based access control (Owner, Admin, Editor, Viewer)
* **📁 Project & Module Management**: Organize documents hierarchically by projects and modules
* **⚡ Vector Search**: Fast semantic search using ChromaDB and Sentence Transformers
* **🔄 Async Processing**: Background document indexing with Celery workers
* **🎨 Modern UI**: Beautiful, responsive interface built with Next.js 15 and Tailwind CSS
* **🐳 Docker Ready**: Complete containerization for easy deployment
* **📊 Task Monitoring**: Real-time task status tracking and progress updates
* **🔐 Secure Authentication**: Token-based authentication with user management

## 🏗️ Architecture
```text
┌────────────┐       ┌──────────────────┐       ┌────────────────────┐
│ Next.js UI │   ←→  │ Django REST API  │   ←→  │ SQLite / PostgreSQL│
│ (Port 3000)│       │   (Port 8000)    │       │                    │
└────────────┘       └──────────────────┘       └────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ ChromaDB   │    │  Celery    │    │   Redis    │
     │  (Vector)  │    │ (Workers)  │    │  (Cache)   │
     └────────────┘    └────────────┘    └────────────┘
```

## 🚀 Quick Start with Docker
#### Prerequisites
* Docker & Docker Compose
* Git

#### Installation
1. Clone the repository  
```bash
git clone https://github.com/yourusername/sop-rag.git
cd sop-rag
```
2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your API keys
```
3. Start with Docker
```bash
docker-compose up --build
```
4. Access the application
* Frontend: http://localhost:3000
* Backend API: http://localhost:8000
* Django Admin: http://localhost:8000/admin


## 🛠️ Technology Stack
#### Backend
* Django 5.2.6 - Web framework
* Django REST Framework - API development
* Celery - Asynchronous task queue
* Redis - Caching and message broker
* SQLite/PostgreSQL - Database
* ChromaDB - Vector database
* LangChain - LLM orchestration
* Sentence Transformers - Text embeddings (all-MiniLM-L6-v2)

#### Frontend
* Next.js 15 - React framework with App Router
* TypeScript - Type safety
* Tailwind CSS - Styling
* React Query - Data fetching and caching
* Axios - HTTP client

#### AI/ML
* Mistral AI - Language model for question answering
* ChromaDB - Vector storage for semantic search
* LangChain - RAG pipeline orchestration
* Sentence Transformers - Document embeddings


## 📖 Project Structure
```text
SOP_RAG/
├── backend/
│   ├── sop_rag/              # Django project settings
│   ├── rag_app/              # Main app (users, projects, modules)
│   ├── vectordb/             # Vector DB & RAG logic
│   │   ├── tasks.py          # Celery tasks
│   │   ├── chat_bot.py       # RAG chatbot implementation
│   │   └── views.py          # API endpoints
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── app/                  # Next.js app directory
│   │   ├── dashboard/        # Dashboard page
│   │   ├── projects/         # Project pages
│   │   └── login/            # Authentication
│   ├── components/           # React components
│   ├── lib/                  # Utilities & API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml        # Docker orchestration
├── .env.example              # Environment variables template
├── .gitignore
└── README.md
```

## 🔧 Configuration
Environment Variables
Create a .env file in the project root:
```bash
# AI API Keys
LANGCHAIN_API_KEY=your-langchain-key
MISTRAL_API_KEY=your-mistral-key

# Database (SQLite by default)
DATABASE_ENGINE=sqlite3

# Redis & Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=django-db

# Vector DB
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
VECTOR_STORE=chromadb

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 API Endpoints
#### Authentication
* POST /api/login/ - User login
* GET /api/user_info/ - Get current user info

#### Projects
* GET /api/projects/ - List all projects
* POST /api/projects/ - Create new project
* GET /api/projects/{id}/ - Get project details
* PUT /api/projects/{id}/ - Update project
* DELETE /api/projects/{id}/ - Delete project

#### Modules
* GET /api/projects/{id}/modules/ - List modules in project
* POST /api/modules/ - Create new module
* GET /api/modules_details/{id}/ - Get module details
* POST /api/modules/{id}/documents/ - Upload documents

#### Vector DB & Chat
* POST /api/vectordb/create/{module_id}/ - Create vector store
* GET /api/vectordb/tasks/?module_id={id} - Get task status
* GET /api/vectordb/chat_session/{module_id}/ - List chat sessions
* POST /api/vectordb/chat/{module_id}/ - Send chat message
* POST /api/vectordb/rating/{answer_id}/ - Rate answer

#### User Management
* GET /api/search_users/?q={query} - Search users
* GET /api/projects/{id}/members/ - List project members
* POST /api/projects/{id}/members/ - Add member
* DELETE /api/projects/{id}/members/{user_id}/ - Remove member

## 🐳 Docker Commands
``` bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f celery

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up --build

# Remove everything including volumes
docker-compose down -v

# Access Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## 💻 Local Development (without Docker)
#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```
#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Run Celery Worker
```bash
cd backend
celery -A sop_rag worker -l info
```
Run Celery Beat (Scheduler)
```bash
cd backend
celery -A sop_rag beat -l info
```

## 📝 Usage
1. **Create a Project**

   Navigate to the dashboard and create a new project to organize your documents.
2. **Add Team Members**
   
   Invite users and assign roles (Owner, Admin, Editor, Viewer).
3. **Create Modules**
   
   Within each project, create modules for different document sets or topics.
4. **Upload Documents**
   
   Upload PDFs, Word documents, or text files to your modules.
5. **Index Documents**
   
   Start the vectorization process to create embeddings for semantic search.
6. **Start Chatting**
   
   Ask questions and get AI-powered answers with source citations from your documents.

## 🎯 Features in Detail
#### RAG Pipeline
1. **Document Processing:** Extract text from uploaded documents
2. **Chunking:** Split documents into manageable chunks (1000 tokens with 200 overlap)
3. **Embedding:** Convert chunks to vectors using Sentence Transformers
4. **Storage:** Store vectors in ChromaDB for fast retrieval
5. **Retrieval:** Find relevant chunks based on query similarity
6. **Generation:** Use Mistral AI to generate answers from retrieved context

#### Chat Sessions
* Create unlimited chat sessions per module
* View chat history
* Session-based context retention
* Rate answers (thumbs up/down)
* Source citations for all answers

#### Task Management
* Background processing with Celery
* Real-time task status updates
* Progress tracking
* Error handling and retry logic

## 🧪 Testing
```bash
# Run backend tests
cd backend
python manage.py test

# Run frontend tests
cd frontend
npm test

# Check Celery status
docker-compose exec celery celery -A sop_rag inspect active
```

## 🚀 Deployment
#### Docker Deployment
The project is production-ready with Docker. 

Deploy to:
* AWS ECS/EKS
* Google Cloud Run
* DigitalOcean App Platform
* Azure Container Instances

#### Environment Setup
##### For production:
1. Set `DATABASE_ENGINE=postgresql` in `.env`
2. Update `DEBUG=False` in Django settings
3. Set strong `SECRET_KEY`
4. Configure proper CORS settings
5. Use environment-specific `.env` files

## 🐛 Troubleshooting
Common Issues

Celery can't connect to Redis:

```bash
# Check Redis is running
docker-compose logs redis

# Restart Celery
docker-compose restart celery
```
Database errors:
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Reset database
docker-compose down -v
docker-compose up --build
```

Frontend not loading:
```bash
# Check logs
docker-compose logs frontend

# Rebuild
docker-compose build frontend
docker-compose up frontend
```

## 👨‍💻 Authors
Mohit Agrawal - [GitHub](https://github.com/Mohit2703/) | [LinkedIn](https://www.linkedin.com/in/mohit2703/)

## 🙏 Acknowledgments
* **LangChain** for RAG orchestration
* **ChromaDB** for vector storage
* **Mistral AI** for language models
* The **Django** and **Next.js** communities
* **Perplexity** and **claude.ai** for code assisstance

## 📧 Contact
For questions or support, please open an issue or contact [mohit27agrawal@gmail.com](mailto:mohit27agrawal@gmail.com)
