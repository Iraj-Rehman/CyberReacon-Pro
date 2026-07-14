# CyberRecon-Pro

A reconnaissance and network analysis dashboard built as my first practical cybersecurity project.

---

## Project Overview

CyberRecon-Pro is a web-based tool that scans a target system or network, checks open/closed ports, discovers connected devices, and displays the results on a dashboard with basic risk scoring.

I built this project to move past just reading about cybersecurity concepts and actually implement one myself. Instead of following a tutorial step by step, I wanted to design and build something on my own — from the scanning logic in the backend to the dashboard that displays the results.

---

## Objective

I built this project for a few reasons:

- To apply the cybersecurity concepts I had been learning in a real, working project instead of just theory.
- To understand how a frontend and backend actually communicate with each other in a live application.
- To practice Python for backend development, specifically for tasks like port scanning and network discovery.
- To get comfortable with the full process of building something — planning it, writing the code, testing it, and fixing what breaks.

Through building it, I learned a lot about how reconnaissance tools work internally, how to structure a backend so it stays manageable as features are added, and how much time debugging actually takes compared to writing the initial code.

---

## Features

- **Overview dashboard** — shows a summary of the last scan, including last target, resolved IP, open/closed ports, scan duration, and an overall risk score.
- **System resource monitoring** — displays live CPU usage, RAM usage, and packets sent/received during scans.
- **Scan Console** — lets you enter a target IP, choose a scan type (e.g. quick scan), and watch scan progress through a live terminal-style log.
- **Port results table** — lists scanned ports with their service name, state (open/closed), risk level, and version info where available.
- **Network Discovery** — performs a ping-sweep across a subnet to find live devices, showing their IP, hostname, and MAC address.
- **Analytics page** — visual breakdown of scan data, including open vs closed ports, risk level distribution, top services found, and scan duration history.
- **Scan History** — keeps a searchable log of past scans with date, target, scan type, duration, open ports, and risk score, along with options to export results.
- **Security Intelligence reference** — a built-in table of common ports and services with their associated risk level and a short explanation of why each one matters. This is also used internally to auto-classify scan findings.

---

## How It Works

The project follows a simple frontend-backend structure:

1. The user interacts with the frontend (dashboard) — for example, entering a target IP and starting a scan.
2. The frontend sends that request to the backend over HTTP.
3. The backend (written in Python) processes the request — running the scan, checking ports, gathering network information, and calculating risk levels.
4. The backend sends the results back to the frontend.
5. The frontend displays the results on the dashboard — in tables, charts, and the live scan log.

---

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python
- **Other tools:** Local HTTP server (`http.server`) for serving the frontend, Git and GitHub for version control

---

## Installation & Running the Project

Follow these steps to run CyberRecon-Pro on your own machine.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/CyberRecon-Pro.git
cd CyberRecon-Pro
```

### 2. Start the frontend

Open a terminal, then run:

```bash
cd frontend
py -m http.server 5500
```

### 3. Start the backend

Open a second terminal, then run:

```bash
cd backend
py app.py
```

### 4. Open the application

Once both servers are running, open your browser and go to:

```
http://127.0.0.1:5500
```

Note: both the frontend and backend need to be running at the same time for the dashboard to work properly.

---


## Learning Experience

This was my first practical cybersecurity project, and it was not a smooth process from start to finish.

I ran into several issues along the way — getting the frontend and backend to communicate correctly took a few attempts, and I had to deal with unexpected outputs and errors in the Python scanning logic. There were times where nothing crashed, but the results were still wrong, which forced me to slow down and actually trace through each part of the code to find the issue.

Testing everything on my own laptop and local network helped a lot, since I could compare the scan results against what I already knew about my own setup. This made debugging more grounded and helped me understand what the tool was actually doing at each step, not just what it was supposed to do.

By the end of it, I had a much better understanding of how frontend and backend components connect, how to structure a Python backend, and how to debug issues methodically instead of guessing. This project also gave me the confidence to keep building more cybersecurity-related tools going forward.

---

## Future Improvements

This project is still a work in progress, and there are several things I plan to improve:

- Adding more scan types and more detailed port/service analysis.
- Improving the accuracy of risk scoring.
- Expanding network discovery to show more device information.
- Cleaning up and optimizing the backend code as I learn better practices.
- Adding proper error handling for edge cases I haven't covered yet.

---

## Conclusion

CyberRecon-Pro represents where I currently am in my cybersecurity learning journey — not a finished product, but a genuine attempt at applying what I've learned in a working project. Building it taught me more than I expected, and I plan to keep learning and building on top of it as I continue improving my skills.
