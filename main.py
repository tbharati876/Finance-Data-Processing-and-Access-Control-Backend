import os
import threading
import time
from datetime import datetime
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pyngrok import ngrok
import uvicorn

# --- 1. DATABASE & MODELS SETUP ---
DATABASE_URL = "sqlite:///./finance_dashboard.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class UserRole(str, Enum):
    ADMIN = "Admin"
    ANALYST = "Analyst"
    VIEWER = "Viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    role = Column(String, default=UserRole.VIEWER)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    type = Column(String) # "Income" or "Expense"
    category = Column(String)
    description = Column(String)
    date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Seed Initial Data
db = SessionLocal()
if not db.query(Transaction).first():
    db.add_all([
        Transaction(amount=5000, type="Income", category="Salary", description="Monthly Pay"),
        Transaction(amount=1200, type="Expense", category="Rent", description="Apartment"),
        Transaction(amount=250, type="Expense", category="Food", description="Groceries")
    ])
    db.commit()
db.close()

# --- 2. BACKEND LOGIC ---
app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def check_permission(required_roles: List[UserRole], user_role: str):
    if user_role not in required_roles:
        raise HTTPException(status_code=403, detail="Access Denied")

@app.get("/api/summary")
def get_summary(user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    check_permission([UserRole.ADMIN, UserRole.ANALYST], user_role)
    income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "Income").scalar() or 0
    expenses = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "Expense").scalar() or 0
    return {"income": income, "expenses": expenses, "balance": income - expenses}

@app.get("/api/transactions")
def list_tx(user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(Transaction.date.desc()).all()

@app.post("/api/transactions")
def add_tx(amount: float, type: str, category: str, user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    check_permission([UserRole.ADMIN], user_role)
    new_tx = Transaction(amount=amount, type=type, category=category, description="Manual Entry")
    db.add(new_tx)
    db.commit()
    return {"status": "success"}

# --- 3. FRONTEND ---
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
        <style>
            body { background: #eceff1; padding: 20px; }
            .card { border-radius: 15px; }
            .summary-box { padding: 15px; color: white; border-radius: 10px; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h4>Finance Dashboard</h4>
            <div class="card-panel">
                <h6>Simulate Role:</h6>
                <button onclick="setRole('Viewer')" class="btn-small grey">Viewer</button>
                <button onclick="setRole('Analyst')" class="btn-small blue">Analyst</button>
                <button onclick="setRole('Admin')" class="btn-small red">Admin</button>
                <span id="role_label" class="badge blue white-text">Role: Viewer</span>
            </div>

            <div id="summary_div" class="row" style="display:none;">
                <div class="col s4"><div class="summary-box green">Income: <span id="s_in"></span></div></div>
                <div class="col s4"><div class="summary-box red">Expense: <span id="s_ex"></span></div></div>
                <div class="col s4"><div class="summary-box blue">Net: <span id="s_net"></span></div></div>
            </div>

            <div id="admin_div" class="card-panel" style="display:none;">
                <h6>Add Record (Admin Only)</h6>
                <input id="amt" type="number" placeholder="Amount">
                <input id="cat" type="text" placeholder="Category">
                <button onclick="save()" class="btn green">Save</button>
            </div>

            <table class="card white">
                <thead><tr><th>Category</th><th>Type</th><th>Amount</th></tr></thead>
                <tbody id="table_body"></tbody>
            </table>
        </div>
        <script>
            let role = "Viewer";
            function setRole(r) { role = r; document.getElementById('role_label').innerText = "Role: "+r; load(); }
            
            async function load() {
                const txRes = await fetch('/api/transactions', {headers: {'user-role': role}});
                const txs = await txRes.json();
                document.getElementById('table_body').innerHTML = txs.map(t => `<tr><td>${t.category}</td><td>${t.type}</td><td>$${t.amount}</td></tr>`).join('');
                
                const sumRes = await fetch('/api/summary', {headers: {'user-role': role}});
                const sDiv = document.getElementById('summary_div');
                if(sumRes.ok) {
                    const s = await sumRes.json();
                    sDiv.style.display = 'block';
                    document.getElementById('s_in').innerText = "$"+s.income;
                    document.getElementById('s_ex').innerText = "$"+s.expenses;
                    document.getElementById('s_net').innerText = "$"+s.balance;
                } else { sDiv.style.display = 'none'; }
                
                document.getElementById('admin_div').style.display = (role === 'Admin') ? 'block' : 'none';
            }
            async function save() {
                const a = document.getElementById('amt').value;
                const c = document.getElementById('cat').value;
                await fetch(`/api/transactions?amount=${a}&type=Expense&category=${c}`, {method:'POST', headers:{'user-role':'Admin'}});
                load();
            }
            load();
        </script>
    </body>
    </html>
    """

# --- 4. DEPLOYMENT (NGROK + UVICORN) ---
NGROK_TOKEN = "36mSHpSl4DWk4VZO6zTudKO3Piz_2ReYvKNYAz8zPKgUJRMxH"

def setup_tunnel():
    ngrok.set_auth_token(NGROK_TOKEN)
    # Open a tunnel on port 10000 (Render's default port)
    public_url = ngrok.connect(10000).public_url
    print(f"\n\n🚀 FINANCE DASHBOARD LIVE AT: {public_url}\n\n")

if __name__ == "__main__":
    setup_tunnel()
    uvicorn.run(app, host="0.0.0.0", port=10000)
