import os
from datetime import datetime
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

#1. DATABASE & MODELS SETUP 
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
    is_active = Column(Integer, default=1)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    type = Column(String)
    category = Column(String)
    description = Column(String)
    date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

#2. SEEDING INITIAL DATA
db = SessionLocal()
if not db.query(User).first():
    
    users = [
        User(username="admin_user", role=UserRole.ADMIN),
        User(username="analyst_user", role=UserRole.ANALYST),
        User(username="viewer_user", role=UserRole.VIEWER),
    ]
    db.add_all(users)
    
    txs = [
        Transaction(amount=5000, type="Income", category="Salary", description="Monthly Pay"),
        Transaction(amount=1200, type="Expense", category="Rent", description="Apartment"),
        Transaction(amount=200, type="Expense", category="Food", description="Groceries"),
        Transaction(amount=150, type="Income", category="Freelance", description="Logo Design"),
    ]
    db.add_all(txs)
    db.commit()
db.close()

# 3. BACKEND LOGIC & ACCESS CONTROL 
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_permission(required_roles: List[UserRole], user_role: str):
    if user_role not in required_roles:
        raise HTTPException(status_code=403, detail="Insufficient Permissions")

#4. API ENDPOINTS 

@app.get("/api/summary")
def get_dashboard_summary(user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    check_permission([UserRole.ADMIN, UserRole.ANALYST], user_role)
    
    income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "Income").scalar() or 0
    expenses = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "Expense").scalar() or 0
    
    category_totals = db.query(Transaction.category, func.sum(Transaction.amount)).group_by(Transaction.category).all()
    
    return {
        "total_income": income,
        "total_expenses": expenses,
        "net_balance": income - expenses,
        "categories": {cat: amt for cat, amt in category_totals}
    }

@app.get("/api/transactions")
def list_transactions(type: Optional[str] = None, user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if type:
        query = query.filter(Transaction.type == type)
    return query.order_by(Transaction.date.desc()).all()

@app.post("/api/transactions")
def create_transaction(amount: float, type: str, category: str, desc: str, user_role: str = Header("Viewer"), db: Session = Depends(get_db)):
    check_permission([UserRole.ADMIN], user_role) # Only Admin can Create
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    new_tx = Transaction(amount=amount, type=type, category=category, description=desc)
    db.add(new_tx)
    db.commit()
    return {"message": "Record Created"}

# --- 5. FRONTEND DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Finance Dashboard</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            body { background: #f5f7f9; }
            .stat-card { padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px; }
            .income-bg { background: #43a047; }
            .expense-bg { background: #e53935; }
            .balance-bg { background: #1e88e5; }
            .role-badge { padding: 5px 10px; border-radius: 5px; background: #eee; font-weight: bold; }
        </style>
    </head>
    <body>
        <nav class="blue-grey darken-4">
            <div class="nav-wrapper container">
                <a href="#" class="brand-logo">FinanceApp</a>
                <ul id="nav-mobile" class="right">
                    <li><span id="current_role_display" class="role-badge">Role: Viewer</span></li>
                </ul>
            </div>
        </nav>

        <div class="container" style="margin-top: 30px;">
            <div class="row card-panel">
                <div class="col s12 m6">
                    <p><b>Simulate User Role:</b></p>
                    <button onclick="setRole('Viewer')" class="btn-flat grey lighten-3">Viewer</button>
                    <button onclick="setRole('Analyst')" class="btn-flat grey lighten-3">Analyst</button>
                    <button onclick="setRole('Admin')" class="btn-flat grey lighten-3">Admin</button>
                </div>
            </div>

            <div id="summary_section" class="row" style="display:none;">
                <div class="col s12 m4">
                    <div class="stat-card income-bg">
                        <h6>Total Income</h6>
                        <h4 id="sum_income">$0</h4>
                    </div>
                </div>
                <div class="col s12 m4">
                    <div class="stat-card expense-bg">
                        <h6>Total Expenses</h6>
                        <h4 id="sum_expense">$0</h4>
                    </div>
                </div>
                <div class="col s12 m4">
                    <div class="stat-card balance-bg">
                        <h6>Net Balance</h6>
                        <h4 id="sum_balance">$0</h4>
                    </div>
                </div>
            </div>

            <div id="admin_form" class="card-panel" style="display:none;">
                <h5>Add New Transaction</h5>
                <div class="row">
                    <div class="input-field col s3"><input id="tx_amt" type="number" placeholder="Amount"></div>
                    <div class="input-field col s3">
                        <select id="tx_type" class="browser-default">
                            <option value="Income">Income</option>
                            <option value="Expense">Expense</option>
                        </select>
                    </div>
                    <div class="input-field col s3"><input id="tx_cat" type="text" placeholder="Category"></div>
                    <div class="input-field col s3">
                        <button onclick="addTransaction()" class="btn green block">Save</button>
                    </div>
                </div>
            </div>

            <div class="card white">
                <div class="card-content">
                    <span class="card-title">Recent Transactions</span>
                    <table class="striped">
                        <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Type</th><th>Amount</th></tr></thead>
                        <tbody id="tx_table"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let currentRole = "Viewer";

            function setRole(role) {
                currentRole = role;
                document.getElementById('current_role_display').innerText = "Role: " + role;
                refreshData();
            }

            async function refreshData() {
                // Fetch Transactions (Available to everyone)
                const txRes = await fetch('/api/transactions', { headers: {'user-role': currentRole} });
                const txData = await txRes.json();
                renderTable(txData);

                // Fetch Summary (Analysts & Admins only)
                const sumRes = await fetch('/api/summary', { headers: {'user-role': currentRole} });
                const sumSec = document.getElementById('summary_section');
                
                if (sumRes.ok) {
                    const sumData = await sumRes.json();
                    sumSec.style.display = 'block';
                    document.getElementById('sum_income').innerText = "$" + sumData.total_income;
                    document.getElementById('sum_expense').innerText = "$" + sumData.total_expenses;
                    document.getElementById('sum_balance').innerText = "$" + sumData.net_balance;
                } else {
                    sumSec.style.display = 'none';
                }

                // Show/Hide Admin Form
                document.getElementById('admin_form').style.display = (currentRole === 'Admin') ? 'block' : 'none';
            }

            function renderTable(data) {
                const html = data.map(t => `
                    <tr>
                        <td>${new Date(t.date).toLocaleDateString()}</td>
                        <td>${t.description}</td>
                        <td>${t.category}</td>
                        <td class="${t.type === 'Income' ? 'green-text' : 'red-text'}">${t.type}</td>
                        <td>$${t.amount}</td>
                    </tr>`).join('');
                document.getElementById('tx_table').innerHTML = html;
            }

            async function addTransaction() {
                const amt = document.getElementById('tx_amt').value;
                const type = document.getElementById('tx_type').value;
                const cat = document.getElementById('tx_cat').value;
                
                const res = await fetch(`/api/transactions?amount=${amt}&type=${type}&category=${cat}&desc=Manual+Entry`, {
                    method: 'POST',
                    headers: {'user-role': 'Admin'}
                });
                
                if(res.ok) {
                    alert("Success!");
                    refreshData();
                } else {
                    alert("Error: " + (await res.json()).detail);
                }
            }

            // Initial load
            refreshData();
        </script>
    </body>
    </html>
    """
