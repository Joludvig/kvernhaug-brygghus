@echo off
cd /d "C:\Users\jolud\OneDrive\Kvernhaug Brygghus"
start "" http://localhost:8501
"C:\Users\jolud\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.port 8501
