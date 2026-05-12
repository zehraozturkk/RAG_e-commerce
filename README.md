# RAG E-Commerce

A Retrieval-Augmented Generation (RAG) project for querying e-commerce order data by combining **PostgreSQL**, **Pinecone**, **OpenAI**, and **sentence-transformer embeddings**. This repository demonstrates how structured transactional data can be transformed into vector embeddings and used to answer natural language questions such as **"Who bought a specific product?"**.

## Project Overview

This project builds an end-to-end prototype that:

- extracts e-commerce order data from PostgreSQL,
- enriches and groups the data into meaningful text records,
- converts those records into vector embeddings,
- stores the embeddings in Pinecone,
- retrieves the most relevant records for a user query,
- and generates natural language answers with an LLM.

The repository includes both:

- a **LangChain-based RAG implementation**, and
- a **custom RAG pipeline without LangChain**.

This makes the project useful both as a working demo and as a comparative learning resource for understanding different RAG integration approaches.

## Architecture

The system follows a simple RAG workflow:

1. **Data Extraction**  
   Order, user, and product data are fetched from PostgreSQL.
2. **Data Transformation**  
   Orders are grouped by user and date, then converted into descriptive text.
3. **Embedding Generation**  
   SentenceTransformer models generate vector embeddings.
4. **Vector Storage**  
   Embeddings and metadata are uploaded to Pinecone.
5. **Retrieval**  
   Relevant records are retrieved based on semantic similarity.
6. **Answer Generation**  
   OpenAI models generate a human-readable response using retrieved context.

## Repository Structure

- `main.py` — simple CLI entry point for asking questions
- `without_langchain.py` — custom RAG pipeline built directly with Pinecone + OpenAI
- `RAG_with_langchin.py` — LangChain-based RAG implementation
- `postgre_to_pinecone.py` — PostgreSQL-to-Pinecone data ingestion pipeline
- `connect_db.py` — PostgreSQL connection helper
- `postgr_to_pinecone.ipynb` — notebook-based experimentation and data flow testing
- `requirements.txt` — project dependencies

## Technologies Used

- **Python**
- **PostgreSQL**
- **Pinecone**
- **OpenAI API**
- **SentenceTransformers**
- **LangChain**
- **python-dotenv**
- **Jupyter Notebook**

## How It Works

### 1. Data Ingestion
The ingestion pipeline in `postgre_to_pinecone.py`:

- connects to PostgreSQL,
- joins `users`, `orders`, and `products` tables,
- groups purchases by user and order date,
- creates a natural-language summary of each order,
- generates embeddings with `all-MiniLM-L12-v2`,
- uploads vectors and metadata to Pinecone.

Example transformed text:

> User Dana Smith ordered Shampoo (Yellow) and Soap (Personal Care) on 2024-12-01

### 2. Retrieval and Question Answering
The retrieval layer searches Pinecone for the most relevant vectors using the user’s natural language query.

Then the selected context is passed to an OpenAI model to generate an answer.

Example questions:

- Who bought Shampoo (Yellow)?
- Which users purchased a certain item?
- What products were ordered on a given date?

### 3. Two RAG Approaches

#### Without LangChain
`without_langchain.py` implements the pipeline manually:

- query embedding generation,
- Pinecone search,
- context construction,
- OpenAI chat completion.

This version is useful for understanding the low-level mechanics of RAG.

#### With LangChain
`RAG_with_langchin.py` uses:

- `HuggingFaceEmbeddings`
- `PineconeVectorStore`
- `RetrievalQA`
- `ChatOpenAI`

This version provides a more modular and framework-oriented implementation.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/zehraozturkk/RAG_e-commerce.git
cd RAG_e-commerce
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

### 4. Configure PostgreSQL connection
Update the database credentials in `connect_db.py` to match your local PostgreSQL environment.

Expected database information currently includes:

- host: `localhost`
- database: `e-commerce`
- port: `5432`

You should replace hardcoded credentials with secure environment variables before using this project in production.

## Usage

### Step 1: Load data into Pinecone
Run the ingestion pipeline:

```bash
python postgre_to_pinecone.py
```

### Step 2: Start the CLI application

```bash
python main.py
```

Then ask a question in natural language.

Type `x` to return to the menu.

## Example Use Case

A user asks:

> Who bought a Shampoo (Yellow)?

The system:

1. converts the question into an embedding,
2. retrieves the most relevant order records from Pinecone,
3. sends the retrieved context to the LLM,
4. returns a natural language answer listing matching users and related purchase details.

## Educational Value

This repository is especially useful for:

- learning the fundamentals of Retrieval-Augmented Generation,
- understanding how structured relational data can be used in semantic search,
- comparing framework-based and framework-free RAG implementations,
- experimenting with vector databases in an e-commerce scenario.

## Current Limitations

- some configuration values are hardcoded,
- dependency versions are only partially pinned,
- file naming and code organization can be improved,
- there are inconsistent namespace/index names across files,
- the project is currently more prototype-oriented than production-ready.

## Suggested Improvements

- move database credentials to environment variables,
- add a proper `.env.example`,
- standardize Pinecone index and namespace names,
- add unit tests and integration tests,
- improve error handling and logging,
- expose the system through an API or web interface,
- rename files for consistency (for example `RAG_with_langchin.py` → `RAG_with_langchain.py`).

## Security Note

Sensitive credentials should never be hardcoded in source files. If this repository is going to be shared or deployed publicly, make sure all database passwords and API keys are stored securely using environment variables or a secrets manager.

## Future Roadmap

Potential next steps for this project include:

- adding metadata filters for more precise retrieval,
- implementing reranking for better answer quality,
- creating a web UI for interactive querying,
- supporting more advanced analytics over order history,
- extending the dataset with customer and product behavior insights.

## License

No license has been specified for this repository yet. If you plan to make this project reusable by others, consider adding an open-source license.

---

If you want, I can also prepare a **more concise startup-focused README**, a **fully Turkish README**, or a **bilingual Turkish-English README** for this repository.