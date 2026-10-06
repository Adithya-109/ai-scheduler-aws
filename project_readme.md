# AI-Powered Cloud-Edge Workload Scheduler

An intelligent, distributed workload orchestration system that dynamically routes Python computational payloads between a local edge node and an AWS EC2 cloud instance to minimize overall execution latency.

## 🚀 Project Overview

This system utilizes an **Abstract Syntax Tree (AST)** parser to statically analyze Python scripts before execution. It extracts 9 structural complexity features and uses **Log-Scaled Histogram Gradient Boosting Regressors** to predict execution times on both local hardware and remote cloud infrastructure. Based on these predictions and real-time network Round Trip Time (RTT), the scheduler dispatches the workload to the most optimal node.

### Key Features
*   **Static AST Feature Extraction:** Analyzes code complexity (loop depth, matrix operations, heavy libraries) without executing it in an isolated environment.
*   **Magnitude Skew Resolution:** Utilizes mathematical log-10 transformations to maintain high prediction accuracy across varying workload magnitudes (from $O(1)$ to $O(N^3)$).
*   **Distributed 3-Tier Architecture:** Seamlessly integrates a Local UI Controller, a Local Edge Worker, and an AWS EC2 Cloud Worker via REST endpoints.
*   **Dynamic Load Balancing:** Achieves a 70–80% optimal routing accuracy by evaluating compute-heavy tasks against network transmission penalties.

---

## 🏗️ System Architecture

1.  **Terminal 1: Controller & UI (Local)** - Runs the Streamlit dashboard (`app.py`), extracts features, queries the ML models, makes routing decisions, and dispatches payloads.
2.  **Terminal 2: Cloud Worker Node (AWS EC2)** - An Ubuntu instance running a background FastAPI execution server, designed to handle computationally heavy, polynomial-time algorithms.
3.  **Terminal 3: Edge Worker Node (Local)** - A local execution server prioritizing lightweight, immediate tasks to avoid network round-trip delays.

---

## 🛠️ Prerequisites

*   Python 3.8+
*   An active AWS Account with an EC2 Instance (Ubuntu)
*   An SSH Key (`.pem` file) for AWS access

---

## 💻 Installation & Setup

**1. Clone the repository**
```bash
git clone https://github.com/Adithya-109/ai-scheduler-aws.git
cd ai-scheduler-aws
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

*(Note: Ensure your AWS `orchestrator-key.pem` is placed in a secure location and added to `.gitignore` to prevent accidental commits).*

---

## 🚦 Usage (Boot Sequence)

To run the full 3-node distributed system, follow this specific terminal boot sequence:

**Step 1: Start the Cloud Node (AWS EC2)**
Start your EC2 instance from the AWS Console and note the new Public IPv4 Address.
```bash
ssh -i "orchestrator-key.pem" ubuntu@<YOUR_AWS_IP>
source .venv/bin/activate
nohup python worker/worker_server.py > worker.log 2>&1 &
```

**Step 2: Start the Edge Node (Local Terminal)**
Open a new local terminal and start the edge worker:
```bash
source .venv/bin/activate
python worker/worker_server.py
```

**Step 3: Launch the Master Scheduler (Local Terminal)**
Open a primary terminal and boot the Streamlit dashboard:
```bash
source .venv/bin/activate
streamlit run app.py
```
*Once the UI opens, expand the **System Endpoints** configuration drawer and update the Cloud Worker URL with your active AWS EC2 IP address.*

---

## 📊 Methodology & Performance

The core prediction engine uses `HistGradientBoostingRegressor` trained on empirically generated hardware execution logs. 
*   **AST Complexity Heuristic:** Resolves arbitrary integer scaling by strictly bounding nested loop multipliers and heavy library imports (e.g., NumPy).
*   **Evaluation:** During batch pipeline evaluation, the scheduler routes tasks to the mathematically optimal node 70% to 80% of the time. The 20-30% variance occurs largely within marginal boundary cases where transient network jitter (RTT) temporarily shifts the optimal execution pathway.

---

## 📄 License

This project is licensed under the MIT License.