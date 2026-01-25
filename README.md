# MIMS - Medical Inventory Management System

A modern, high-performance Pharmacy and Medical Inventory Management System built with Django. Designed for speed, accuracy, and a "Money-First" retail approach.

## Key Features

- **Advanced Analytics:** Real-time dashboard showing most moving products, highest profit margins, and 7-day revenue trends.
- **Excel-Style Inventory:** Professional, high-readability ledger for tracking stock levels with integrated live search and low-stock alerts.
- **Money-First Sale Form:** Multi-item sales processing that calculates quantities automatically based on Tsh paid.
- **Loan Tracking:** Dedicated view for managing customer debts and installment payments.
- **Performance Optimized:** Uses `select_related` and debounced searching for instant responsiveness.

---

## Tech Stack

- **Backend:** Django 5.x
- **Frontend:** Tailwind CSS (Modern UI), Chart.js (Analytics)
- **Database:** SQLite (Default) / PostgreSQL ready

---

## How to Run Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/iamsharifukitori/MIMS.git](https://github.com/iamsharifukitori/MIMS.git)
cd MIMS

2. Set Up Virtual Environment (Recommended)
Bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

3. Install Dependencies
Ensure you have Django installed:

Bash
pip install django
4. Database Migrations
Create the database tables based on the models:

Bash
python manage.py makemigrations mims
python manage.py migrate
5. Create Admin Access
Set up your superuser to access the dashboard:

Bash
python manage.py createsuperuser
6. Start the Server
Bash
python manage.py runserver
Visit http://127.0.0.1:8000/dashboard/ to view the system.

Project Structure
Kdevtools/ - Project settings and main URL routing.

mims/ - Core application logic.

templates/mims/ - Modern UI HTML files.

models.py - Database schema with stock-update signals.

views.py - Optimized business logic and analytics.

db.sqlite3 - (Ignored in Git) Local database file.

Business Logic Note: Money-First Approach
This system uses a custom retail logic where the pharmacist enters the Amount Paid (Tsh) first. The system then automatically calculates the Quantity of tablets/units based on the unit price, ensuring faster transactions and reducing manual calculation errors.


---

### Final Step: Push the README
1. Create a file named `README.md` in your project root.
2. Paste the content above.
3. Run these final commands:

```bash
git add README.md
git commit -m "Add professional README documentation"
git push origin main
