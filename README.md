# 📸 Event Photo Finder (AI-Based)

An AI-powered web application that allows users to **find their photos from event albums using selfies**.
Built with **React, Node.js, FastAPI, and DeepFace (ArcFace + FaceNet)**.

---

## 🚀 Features

* 🔍 Upload selfies → find matching event photos
* 👥 Works with **group photos**
* 🧠 Uses **ArcFace + FaceNet512** for high accuracy
* 🧩 Auto face detection & embedding
* 📊 Confidence score & best-match ranking
* 🗂️ Event-based photo organization
* ⚡ Fast indexing and matching

---

## 🏗️ Tech Stack

### Frontend

* React.js
* Vite
* Axios

### Backend

* Node.js
* Express.js

### AI Service

* FastAPI
* DeepFace
* TensorFlow / tf-keras

### Deployment

* Ubuntu (Linux)
* NGINX
* AWS EC2 (optional)
* Cloudflare (SSL)

---

## 📁 Project Structure

```
event-photo-finder/
│
├── client/              # React frontend
├── server/              # Node backend
│   ├── routes/
│   ├── uploads/
│
├── ai-service/          # FastAPI AI service
│   ├── embeddings/
│   ├── face_crops/
│   ├── app.py
│
└── README.md
```

---

## ⚙️ Installation (Linux)

### 1️⃣ Clone Repo

```bash
git clone https://github.com/your-username/event-photo-finder.git
cd event-photo-finder
```

---

## 🔧 Backend Setup (Node.js)

```bash
cd server
npm install
node server.js
```

Runs on:

```
http://localhost:5000
```

---

## 🤖 AI Service Setup (FastAPI)

```bash
cd ai-service

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Run AI server:

```bash
python3 -m uvicorn app:app --reload
```

Runs on:

```
http://localhost:8000
```

---

## ⚠️ IMPORTANT (Model Setup Fix)

If face matching fails:

👉 Delete corrupted models:

```bash
rm -rf /root/.deepface
```

👉 Restart AI server to auto-download models:

```bash
python3 -m uvicorn app:app --reload
```

👉 Ensure files exist:

```bash
ls -lh /root/.deepface/weights
```

Expected:

```
arcface_weights.h5      ~130MB
facenet512_weights.h5   ~90MB
```

---

## 🌐 Frontend Setup

```bash
cd client
npm install
npm run dev
```

Runs on:

```
http://localhost:5173
```

---

## 🔄 Workflow

1. Admin uploads event photos
2. AI detects faces & creates embeddings
3. User uploads selfie
4. System matches faces
5. Matching photos are displayed

---

## 🧠 AI Pipeline

* Face Detection → OpenCV
* Face Embedding → ArcFace + FaceNet512
* Matching → Cosine Similarity
* Clustering → Grouping by identity

---

## 🐞 Common Issues & Fixes

### ❌ No matches found

✔ Fix:

```bash
rm -rf embeddings/*
rm -rf face_crops/*
```

Re-upload event photos

---

### ❌ Faces detected but no embeddings

✔ Cause: corrupted model weights
✔ Fix: delete `.deepface` folder and restart

---

### ❌ "file signature not found"

✔ Cause: incomplete model download
✔ Fix: re-download models

---

## 🌍 Deployment (Ubuntu + NGINX)

### Install NGINX

```bash
sudo apt install nginx -y
```

### Configure reverse proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
    }

    location /api/ {
        proxy_pass http://localhost:5000/api/;
    }

    location /ai/ {
        proxy_pass http://localhost:8000/;
    }
}
```

---

## 🔐 SSL (Free)

Use **Cloudflare**:

* Add domain
* Enable SSL → Flexible
* Done ✅

---

## 📌 Future Improvements

* 🎯 Higher accuracy models (InsightFace)
* 📱 Mobile optimization
* ☁️ Cloud storage (S3)
* ⚡ GPU acceleration
* 🔎 Real-time search

---

## 👨‍💻 Author

Developed by **Sweatha B**

---

## ⭐ Support

If you like this project:

👉 Star the repo ⭐
👉 Share with others 🚀

---
