## Video Demo: https://drive.google.com/file/d/17MjHJJogqC1i0J0ijTxy1UJExzPbwN1o/view?usp=sharing
## Github Repo: https://github.com/tbharati876/Finance-Data-Processing-and-Access-Control-Backend
## Deployed URL: https://finance-data-processing-and-access-c4zz.onrender.com
## Live URL: https://unsignifiable-tera-overbold.ngrok-free.dev/
## Swagger UI: https://unsignifiable-tera-overbold.ngrok-free.dev/docs


# 📊 Finance Dashboard Backend

### Backend Intern Assignment: Financial Management & RBAC System

This project is a robust, production ready backend system designed to manage financial records with integrated **Role-Based Access Control (RBAC)**. It features a FastAPI backend, an SQLite database with SQLAlchemy ORM, and a Materialize CSS frontend dashboard.

---

## 1. Setup & Installation Process

### **Local Deployment**
1. **Clone the Project:**
   ```bash
   git clone <repo-url>
   cd finance-dashboard
   ```
2. **Install Dependencies:**
   ```bash
   pip install fastapi uvicorn sqlalchemy pyngrok
   ```
3. **Run the Application:**
   ```bash
   python main.py
   ```

### **Render Cloud Deployment**
1. Push this code to a GitHub Repository.
2. Connect the Repository to a **Render Web Service**.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python main.py`
5. **Access:** Open the **Logs** tab in Render to find your unique **Ngrok Public URL**.

---

##  2. API Documentation & Logic

The system uses a custom header `user-role` to identify users and enforce permissions.

| Endpoint | Method | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `/` | GET | All | Serves the interactive Frontend Dashboard. |
| `/api/transactions` | GET | Viewer, Analyst, Admin | Fetches all financial entries from the database. |
| `/api/summary` | GET | Analyst, Admin | Returns aggregated data (Income, Expenses, Net). |
| `/api/transactions` | POST | Admin | Adds a new record. Validates amount and type. |


## 3. Access Control Logic (RBAC)

The backend implements a security model to ensure data privacy and integrity:

* **Viewer:** Least privilege. Can only read the transaction history.
* **Analyst:** Medium privilege. Can read history and access the **Dashboard Summary API** for financial insights.
* **Admin:** Full privilege. Can perform all CRUD operations and manage the financial state of the system.

**Implementation Detail:** We use a centralized `enforce_rbac` utility function. This function intercepts every request, validates the `user-role` header against a whitelist for that specific endpoint, and raises a `403 Forbidden` error if the user attempts an unauthorized action.

---

## 4. Assumptions & Tradeoffs

### **Assumptions Made**
* **Stateless Authentication:** For this assignment, I assume the user's role is provided in the request header. In production, this would be derived from a secure **JWT (JSON Web Token)**.
* **Auto-Seeding:** To ensure the evaluator has immediate data to see, the system automatically seeds the database with 4 sample transactions upon the first launch.

### **Tradeoffs Considered**
* **Database Choice (SQLite vs. PostgreSQL):**
    * *Tradeoff:* SQLite is file-based and resets on Render's free tier.
    * *Decision:* I chose **SQLite** for this submission to ensure **Zero Configuration**.
* **Architecture (Monolith vs. Microservice):**
    * *Tradeoff:* Separating frontend and backend.
    * *Decision:* I bundled the HTML/JS frontend within the FastAPI app, simplifying the deployment process.

---

## 5. Accuracy & Failure Cases

### **Functional Accuracy**
* **Mathematical Precision:** The Dashboard Summary uses the `SQL SUM()` function at the database level to ensure 100% calculation accuracy, rather than calculating in Python which can lead to memory overhead.
* **Input Validation:** The system rejects negative amounts and invalid transaction types, maintaining a clean data state.

### **Known Failure Cases / Limitations**
* **Concurrency:** SQLite may experience "Database is locked" errors if thousands of users try to write simultaneously.
* **Auth Spoofing:** Since roles are passed via headers, a malicious user could technically manually change their header to "Admin." (Note: This is addressed in production using signed tokens).
* **Persistence:** Data is lost on server restart (Render Free Tier). A persistent PostgreSQL database is recommended for long-term use.

---

## Requirements
* `fastapi`
* `uvicorn`
* `sqlalchemy`
* `pyngrok`
```
