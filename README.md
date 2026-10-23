# HR Policy and Leave AI Agent

An AI-powered Human Resources assistant developed for **Hacktiv8 AI Engineer — Milestone 2**.

This application helps employees access HR policies through natural-language conversations and supports leave request workflows with human confirmation and manager review.

## Features

- **AI-Powered HR Assistant:** Answers employee questions about HR policies.
- **Retrieval-Augmented Generation (RAG):** Retrieves relevant information from HR policy documents stored in Pinecone.
- **Leave Request Management:** Helps employees prepare and submit leave requests.
- **Human-in-the-Loop Confirmation:** Requires user confirmation before submitting a leave request.
- **Database Integration:** Uses Neon PostgreSQL to store employee and leave request data.
- **Web Interface:** Provides a conversational interface using Streamlit.
- **REST API:** Uses FastAPI to handle AI Agent requests and business logic.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Backend | FastAPI |
| Frontend | Streamlit |
| Large Language Model | OpenAI |
| Vector Database | Pinecone |
| Relational Database | Neon PostgreSQL |
| Containerization | Docker and Docker Compose |
| Testing | Pytest |

## Prerequisites

Before running the application, install:

- Python 3.11
- Git
- Docker Desktop (optional, for containerized execution)

You will also need valid credentials for OpenAI, Pinecone, and Neon PostgreSQL.

## 1. Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/YOUR_USERNAME/hr-agent-milestone2.git
cd hr-agent-milestone2
```

Replace `YOUR_USERNAME` with the actual GitHub username.

## 2. Set Up the Python Environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

For macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## 3. Configure Environment Variables

Create a `.env` file in the project root directory.

Configure the environment variables required by `src/config.py`, including credentials for:

- OpenAI API
- Pinecone
- Neon PostgreSQL
- Any additional services enabled by the application

Use the exact variable names defined in the project's configuration module.

**Security:** Never commit `.env`, API keys, passwords, or database connection strings to GitHub.

## 4. Prepare the Database and Knowledge Base

The project includes scripts for database initialization and Pinecone indexing.

Depending on the environment, run:

```bash
python seed_neon.py
```

Then:

```bash
python index_pinecone.py
```

Ensure that the Neon database schema has been initialized and that the Pinecone index configuration matches the application settings.

These setup steps generally need to be performed only during initial setup or when the underlying data changes.

## 5. Run the FastAPI Backend

Start the backend server:

```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Open the API documentation:

http://localhost:8000/docs

Keep this terminal running.

atau
```bash
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --http h11 --log-level debug
```

## 6. Run the UI Frontend

Open a second terminal in the project directory.

Activate the Python virtual environment and run:

```bash
cd hr-agent-nextjs
npm run dev
```

Open the HR Agent interface:

- Local:        http://127.0.0.1:3000
- Network:      http://127.0.0.1:3000

The frontend must be configured to communicate with the FastAPI backend.

## Run using Link vercel
Accessing the Deployed Application

Users do not need to install Python or Node.js, nor do they need to use a terminal.

Simply open the HR Agent frontend link:

Application URL: https://hr-agent-web-gilt.vercel.app/

The link can be accessed via a web browser on any laptop, computer, or smartphone connected to the internet.

The FastAPI backend runs separately on Vercel and is automatically utilized by the frontend.

## 7. Run with Docker

Build the Docker image:

```bash
docker build -t hr-agent:milestone2 .
```

Run the FastAPI container:

```bash
docker run --rm -p 8000:8000 --env-file .env hr-agent:milestone2
```

Access the API documentation:

http://localhost:8000/docs

### Docker Compose

The repository also includes a `docker-compose.yml` file for running the application using containers.

Build and start the configured services:

```bash
docker compose up --build -d
```

Check running services:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f
```

Stop the containers:

```bash
docker compose down
```

Service URLs depend on the port mappings defined in `docker-compose.yml`.

**Note:** The `.env` file must remain outside the Docker image. Credentials should be provided at runtime.

## 8. Run Automated Tests

Execute the test suite:

```bash
python -m pytest tests/ -v
```

Some integration tests may require live API credentials or additional configuration.

## 9. Project Structure

```text
hr-agent-milestone2/
├── api/                  # Deployment entry point
├── data/                 # HR policies and sample datasets
├── sql/                  # Database schema
├── src/                  # Agent, API, retrieval, and business logic
├── templates/            # Project documentation templates
├── tests/                # Automated tests
├── app.py                # Streamlit frontend
├── demo_personas.json    # Demo user personas
├── seed_neon.py          # Database seeding script
├── index_pinecone.py     # Pinecone indexing script
├── Dockerfile            # Docker image configuration
├── docker-compose.yml    # Multi-container configuration
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project configuration
└── README.md             # Project documentation
```

## 10. Deployment

The application separates the backend and frontend components.

- **Backend:** FastAPI can be deployed to a compatible Python hosting platform.
- **Frontend:** Streamlit can be deployed to Streamlit Community Cloud or another compatible hosting provider.
- **Database:** Neon PostgreSQL.
- **Vector Database:** Pinecone.

For production deployment, configure environment variables in the hosting provider's settings, update the frontend API endpoint, and implement appropriate access controls and usage limits.

## Security Considerations

- Keep API keys and database credentials private.
- Do not store secrets in the Git repository or Docker image.
- Use environment variables for configuration.
- Require explicit confirmation before executing leave request actions.
- Protect employee information and restrict access to sensitive operations.
- Review authentication and authorization before making the application publicly accessible.

## Author

**Syifa Mutaalia**  
Hacktiv8 — AI Engineer  
Milestone 2 Project