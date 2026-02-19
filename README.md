# OpenMRS AI & DHIS2 Integration Bridge

An intelligent, secure, and automated bridge designed to close the gap between clinical data in OpenMRS/Bahmni and public health reporting in DHIS2. This tool leverages Generative AI to transform natural language questions into validated SQL and synchronizes results directly to DHIS2 Data Value Sets.

# Key Features
  Natural Language Querying: Ask questions like *"Show me all ANC visits this month"* and let the AI generate the SQL.
  Security Validator: A robust `validator.py` module ensures all AI-generated SQL is safe, preventing SQL injection and protecting patient privacy.
  DHIS2 Mapping Engine: Automatically maps clinical data to DHIS2 Data Elements and Category Option Combos.
  Rolling Sync Logs: Built-in tracking system that maintains a history of the last 200 synchronizations for transparency and auditing.
  Dark-Theme UI: A modern, responsive dashboard for managing queries, reviewing data, and triggering syncs.

# Tech Stack
  Backend: Python, FastAPI
  AI Logic: LLM Integration (OpenAI/Local)
  Database: MySQL (OpenMRS/Bahmni)
  Frontend: HTML5, CSS3, Vanilla JavaScript
  Integration: DHIS2 Web API
  
# Quick Start

1. Clone the Repository
```bash
> git clone https://github.com/DeepakPNeupane/openmrsdb_ai-dhis2_sync.git
2. create the composer to run quick service for existing bahmni docker
bahmni-ai:
    build:
      context: ./openmrsdb_ai-dhis2_sync
      dockerfile: Dockerfile
    container_name: bahmni-ai
    ports:
      - "9000:9000"
    environment:
      - OPENAI_API_KEY=
      - OPENMRS_DB_NAME=openmrs
      - OPENMRS_DB_HOST=openmrsdb
      - OPENMRS_DB_USERNAME=openmrs-user
      - OPENMRS_DB_PASSWORD=password  

    depends_on:
      - openmrsdb
    networks:
      - bahmni
    restart: unless-stopped

3. Browse the URL http://localhost:9000/ and password is insecure Admin123 to login in (the login is Hardcoded Client Side Authentication Bypass from JavaScript)

By: Deepak Neupane
