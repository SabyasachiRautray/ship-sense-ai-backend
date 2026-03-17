# 🚢 ShipSense AI – Backend

The backend service for **ShipSense AI**, responsible for handling shipment data, delay prediction, alerts, and real-time logistics insights.

---

## 🌟 Features

* 📦 Shipment management APIs
* ⏱️ ETA & SLA tracking
* ⚠️ Delay detection & alert generation
* 🤖 AI-based shipment analysis (delay prediction)
* 📊 Simulation & analytics endpoints
* 🔐 Authentication & role-based access (Admin/User)
* 🌐 RESTful API built with FastAPI

---

## 🛠️ Tech Stack

* **Framework:** FastAPI
* **Language:** Python
* **Database:** MySQL / SQLite (via SQLAlchemy)
* **ORM:** SQLAlchemy
* **Validation:** Pydantic
* **Server:** Uvicorn
* **CORS Handling:** FastAPI Middleware

---

## 📁 Project Structure

```id="6dts4n"
backend/
│── routes/
│   │── shipments.py
│   │── analyze.py
│   │── alerts.py
│   │── simulate.py
│   │── auth.py
│── models/
│── database.py
│── main.py
│── requirements.txt
```

---

## 🚀 Getting Started

### 1. Clone the repo

```id="i1ju1z"
git clone https://github.com/YOUR_USERNAME/ship-sense-ai.git
cd ship-sense-ai/backend
```

### 2. Create virtual environment (recommended)

```id="r62x5f"
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```id="0xlfii"
pip install -r requirements.txt
```

### 4. Run the server

```id="h4ew30"
uvicorn main:app --reload
```

---

## 🌐 API Base URL

```id="mkf67b"
http://127.0.0.1:8000
```

---

## 📌 API Endpoints Overview

| Endpoint     | Description                  |
| ------------ | ---------------------------- |
| `/shipments` | Manage shipment data         |
| `/analyze`   | AI delay prediction          |
| `/alerts`    | Delay alerts & notifications |
| `/simulate`  | Run logistics simulations    |
| `/auth`      | Authentication APIs          |

---

## 📊 Example Shipment Data

```json id="6q2vsy"
{
  "shipment_id": "SHP-1043",
  "origin": "Hyderabad",
  "destination": "Ahmedabad",
  "carrier": "BlueDart",
  "eta": "2026-03-13T06:00:00",
  "sla_deadline": "2026-03-13T08:00:00"
}
```

---

## 🔗 Frontend Integration

Ensure frontend is running and API base URL is configured correctly.

Default CORS setup allows local frontend connection.

---

## ⚡ Future Improvements

* 🤖 Advanced ML models for prediction
* 📡 Real-time tracking via WebSockets
* 🧠 Intelligent routing suggestions
* 🔔 Notification system (Email/SMS)

---



## 📄 License

This project is built for a hackathon and is open for learning purposes.

```
shipsense backend
├─ config.py
├─ database.py
├─ main.py
├─ models
│  └─ shipment.py
├─ requirements.txt
├─ routes
│  ├─ alerts.py
│  ├─ analyze.py
│  ├─ auth.py
│  ├─ shipments.py
│  └─ simulate.py
└─ services
   ├─ auth.py
   ├─ gemini.py
   ├─ news.py
   ├─ traffic.py
   └─ weather.py

```


pip install -r requirements.txt       //to install all the packages


uvicorn main:app --reload // to run the backend