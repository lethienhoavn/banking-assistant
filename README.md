# 💬 AI Assistant on Microsoft Teams

An intelligent chatbot integrated into Microsoft Teams, powered by OpenAI and LangChain for conversational interaction, data analysis, and visualization.

# 🚀 PART 1. DEMO 


<div align="center">
<img src="./images/banking_assistant_demo.png" alt="Banking Assistant Demo" width="1200" align=/>
</div>


## 🔶 1. Key Features

### 🤖 LLM Chat

* Uses `ChatOpenAI` from LangChain.
* Natural language interaction with conversation memory.
* Capable of answering questions across various domains.

### 📊 Text-to-SQL Tool (Text2SQL)

* Users can ask questions in natural language such as:
  `"What is the total products per month?"`
* The bot automatically converts this to SQL, queries the database, and returns results.
* Especially useful for analytics, finance, and accounting teams.

### 📈 Table, HTML and Chart Generation from Data

* The bot can generate table, html / charts directly from query results or uploaded datasets.
* Charts are automatically created and **sent as images into Microsoft Teams**.

### 🔐 User Authentication via Teams ID

* Uses `turn_context.activity.from_property.id` to identify the user.
* No extra login needed – seamlessly integrated with the current Teams account.

### ⚙️ Easily Extendable via LangChain Tools

* The system is designed for easy integration of new tools: celery task, redis memory, retriever, vector search, agent, planner, etc.


## 🔶 2. Key Architecture Explanations

Basically, Text2SQL component works as follows:

<div align="center">
<img src="./images/text2sql.png" alt="Basic Text2SQL Diagram" width="500" align=/>
</div>

<br/>

If we want to dive deeper into the underlying mechanisms, here how each component interacts with each other:

<div align="center">
<img src="./images/detailed_text2sql.png" alt="Detailed Text2SQL Diagram" width="600" align=/>
</div>

## 🔶 3. Project Structure

```
msteams/
├── manifest.json         # Manifest for MS Teams App
src/
├── llm_confg/            # Prompt templates & params for LLM
├── tools/                # LLM tools
    ├── sql.py            # Perform SQL query
    ├── report.py         # Make HTML report
    ├── chart.py          # Make visualization chart (bar, line,...)
├── app.py                # Entry point for aiohttp server
├── handler.py            # LangChainBot logic & adapter
├── config.py             # Config (API key, Redis, Teams App ID)
├── db.sqlite             # SQLite DB with 6 example tables: users, addresses, products, carts, orders, order_products
├── requirements.txt      # Python lib packages need to be installed
Dockerfile                # Dockerfile for deployment 
README.md                 # Documentation
```


## 🔶 4. Deployment

### A. Run Locally

#### Install dependencies:

```bash
pip install -r src/requirements.txt
```

#### Start the server:

```bash
gunicorn --bind=0.0.0.0:3978 --worker-class=aiohttp.worker.GunicornWebWorker --timeout=600 app:app
```


### B. Deploy on AWS

Authen AWS:

```
aws configure
aws ecr get-login-password --region <aws_region> | docker login --username AWS --password-stdin <aws_ecr_address>
```

Then:

```bash
docker build -t teamsbot-aws .
docker tag teamsbot-aws:latest <aws_ecr_address>/teamsbot-aws:latest
docker push <aws_ecr_address>/teamsbot-aws:latest
```

**Note:**

* Before pushing to ECS, you can test locally using:
  `docker run -it -v /home/<user>/ngrok_logs:/src/ngrok_logs -p 3978:3978 teamsbot-aws:latest`
* To quickly expose the API endpoint for development testing:
  `ngrok http 3978 --log=stdout > ngrok_logs/ngrok.log 2>&1`


### C. Register Bot with Microsoft Teams:

1. Log into [Azure Portal](https://portal.azure.com) using your enterprise MS account (`xxx@<your_domain>.onmicrosoft.com`) and create an Azure Bot.
2. Set the bot endpoint to:
   `https://<your-domain>/api/messages`
3. Add the Microsoft Teams channel to the Azure Bot. You can test if the API endpoint is working under Settings > Test in Web Chat.
4. Upload the bot app to Teams using the `msteams/msteams.zip` package.


### D. Sample Prompt (Text2SQL)

> "Show me the top 5 products people ordered"

The bot will auto-generate SQL like:

```sql
SELECT product_id, SUM(amount) as total_amount 
FROM order_products 
GROUP BY product_id 
ORDER BY total_amount 
DESC LIMIT 5;
```



<br>
<br>
<br>



# PART 2. Architecture Design

<div align="center">
<img src="./images/architecture.png" alt="Architecture Diagram" width="1500" align=/>
</div>


## 🔶 1. Key Architecture Components and Explanations

### ✅ A. Microsoft Teams Bot Interface

**Function**:
Main user interface for business teams to ask questions, retrieve data, or receive automated insights.

**Features**:

* Natural language Q\&A (powered by LLM via LangChain)
* Button-driven dashboards for frequently asked queries
* Push notifications (e.g., anomaly alerts or opportunity suggestions)


### ✅ B. API Gateway (Amazon API Gateway + Route 53)

**Function**:

* Routes user requests from Microsoft Teams to backend LLM services
* Handles authentication 
* Adds support for versioning, throttling, and public/private endpoints


### ✅ C. Intelligent Query & Insight Engine

**LLM Orchestration Layer**:

* Built with **LangChain**, **OpenAI GPT** / **finetune LLM**
* Translates natural language into semantic SQL queries or invokes pre-defined pipelines

**Intent & Context Detection**:

* Understands business questions such as
  *"Which B2B customers have high revenue but low digital engagement?"*


### ✅ D. Data Consolidation (Customer 360 Ontology)

**Function**:

* Consolidate disparate data (demographics, segments, transactions, digital activities, etc.) from B2C, B2B, and ImEx systems.
* Standardize and clean data for analytics, ML, and dashboarding.
* Centralize all business-relevant data into a **single source of truth**.

**Benefits**:

* Ensures data consistency across teams
* Centralized governance of KPIs and metrics


### ✅ E. Insight Generation Engine

**ML Models**:

* Churn prediction
* Cross-sell recommendation
* Opportunity detection

**Rules Engine**:

* Implements business rules (e.g., “3-month inactivity + high balance → flag as dormant”)

**Databricks Feature Store**:

* Stores reusable features and model outputs for scoring and retraining
