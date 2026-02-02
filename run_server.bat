@echo off
:: Replace with your project folder path
cd /d "C:\Users\Twaha\Documents\Projects\Kdevtools\"
:: Activate virtual environment and start server
call .\venv\Scripts\activate
python manage.py runserver