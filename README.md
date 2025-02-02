
# **AI - Patrol Dispatch - AI-Enhanced Incident Response Platform**  

OFDWM is a real-time incident response platform designed to optimize police unit deployment. It processes live incident reports, prioritizes response based on severity, and ensures efficient resource allocation to enhance public safety.  

## **Features**  
✅ **Intelligent Deployment:** Assigns police units dynamically based on incident severity and availability.  
✅ **Cost Optimization:** Tracks operational costs and enhances resource efficiency.  
✅ **Real-Time Reporting:** Logs incidents, response times, and deployments for analysis.  
✅ **User-Friendly Interface:** Simplifies data input and report visualization.  

---

## **AI in Project Development**  
We integrated AI tools like **ChatGPT** and **GitHub Copilot** throughout the development process. These tools assisted us in:
- **Syntax Checks & Code Generation**: Ensuring efficient, error-free code and generating sample snippets.
- **Testing & Debugging**: Creating test data and optimizing performance.
- **Learning & Best Practices**: Accelerating our understanding of new technologies and improving our coding standards.

By leveraging AI, we enhanced productivity, streamlined debugging, and adopted best coding practices more efficiently.

---

## **Getting Started**  

### **1. Set up the virtual environment**  
```sh
python3 -m venv venv
```

### **2. Activate the virtual environment**  
- **On macOS/Linux:**  
  ```sh
  source venv/bin/activate
  ```
- **On Windows:**  
  ```sh
  venv\Scripts\activate
  ```

### **3. Install dependencies**  
```sh
pip install -r requirements.txt
```

### **4. Run the project**  
```sh
python3 app/app.py
```

---

## **Project Structure**  
```
/OFDWM
   ├── app/
   │   ├── __pycache__/
   │   ├── static/            # CSS, JavaScript, images
   │   ├── templates/         # HTML templates for UI
   │   │   ├── base.html
   │   │   ├── index.html
   │   │   ├── result.html
   │   ├── app.py             # Main application entry point
   │   ├── config.py          # Configuration settings
   │   ├── extensions.py      # Extensions and helper functions
   │   ├── models.py          # Database models
   │   ├── routes.py          # API endpoints and logic
   ├── venv/                  # Virtual environment (not included in repo)
   ├── .gitignore             # Git ignore file
   ├── LICENSE                # Project license
   ├── README.md              # Project documentation
   ├── requirements.txt       # Project dependencies
```

---

## **API Endpoints**  
### **1. Get all active incidents**  
```http
GET /incidents
```
📌 Returns a list of active incidents with their severity and assigned units.

### **2. Report a new incident**  
```http
POST /incidents
```
📌 Accepts a JSON body with **location, severity, and description** to log a new incident.

---

## **Contributing**  
We welcome contributions! To get started:  
1. **Fork** the repository.  
2. **Create a new branch** for your feature: `git checkout -b feature-name`.  
3. **Commit changes** and push to GitHub.  
4. Open a **pull request** for review.  

---

## **License**  
📜 This project is licensed under the MIT License – see the `LICENSE` file for details.  

---

