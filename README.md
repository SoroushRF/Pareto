![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
<br>
<div align="center">

# 📊 Pareto

### *The 80/20 Student Success Tool*

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

**Stop wasting time on low-impact assignments. Upload your syllabus and let AI optimize your semester.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API Documentation](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 📑 Table of Contents

- [📊 Pareto](#-pareto)
  - [📑 Table of Contents](#-table-of-contents)
  - [🎯 About](#-about)
  - [✨ Features](#-features)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [📋 Prerequisites](#-prerequisites)
  - [🚀 Installation](#-installation)
    - [1. Clone the Repository](#1-clone-the-repository)
    - [2. Backend Setup](#2-backend-setup)
    - [3. Frontend Setup](#3-frontend-setup)
    - [4. Quick Start (Both Servers)](#4-quick-start-both-servers)
  - [⚙️ Configuration](#️-configuration)
  - [📖 Usage](#-usage)
  - [📁 Project Structure](#-project-structure)
  - [🔌 API Documentation](#-api-documentation)
    - [Health Check](#health-check)
    - [Analyze Syllabus](#analyze-syllabus)
  - [🧠 How It Works](#-how-it-works)
  - [🧠 Development Insights & Challenges](#-development-insights--challenges)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)
  - [🙏 Acknowledgments](#-acknowledgments)

---

## 🎯 About

**Pareto** is named after the [Pareto Principle](https://en.wikipedia.org/wiki/Pareto_principle) (also known as the 80/20 rule), which states that roughly 80% of consequences come from 20% of causes.

In the context of academic success, this means that a significant portion of your grade often comes from just a few key assignments. Pareto helps students identify these high-impact assessments by intelligently analyzing course syllabi, allowing them to prioritize their efforts effectively.

> 🎓 **For Students, By Students** — Focus on what matters most and optimize your semester for maximum results with minimum effort.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Syllabus Upload** | Simply drag and drop your syllabus PDF for instant analysis |
| 🤖 **AI-Powered Analysis** | Leverages Google Gemini 2.5 Flash for intelligent document parsing |
| 📊 **Smart Categorization** | Automatically categorizes assignments by impact and type |
| ⚖️ **Weight Analysis** | Identifies high-weight assignments that deserve your attention |
| 🎯 **Priority Sorting** | Ranks assignments by importance (mandatory → high-weight → droppable) |
| 📋 **Policy Extraction** | Extracts late policies, missed work rules, and grading scales |
| 💾 **Export Raw Data** | Download the full analysis as JSON for further use |
| ⚡ **Real-time Status** | See backend connection status and analysis duration |
| 🌙 **Modern Dark UI** | Beautiful, responsive interface with dark mode design |

### Assignment Categories

| Category | Badge | Description |
|----------|-------|-------------|
| **Mandatory** | 🔴 Red | Must complete to pass the course |
| **Transferable** | 🔵 Blue | Weight transfers to another assessment if missed |
| **Drop Rule** | 🟢 Green | Lowest N grades are automatically dropped |
| **Standard** | ⚪ Gray | Regular graded assignment |

---

## 🛠️ Tech Stack

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** — Modern, fast Python web framework
- **[Google Generative AI](https://ai.google.dev/)** — Gemini 2.5 Flash for document analysis
- **[Pydantic](https://docs.pydantic.dev/)** — Data validation using Python type annotations
- **[Uvicorn](https://www.uvicorn.org/)** — Lightning-fast ASGI server

### Frontend
- **[React 19](https://react.dev/)** — UI component library
- **[Vite 7](https://vitejs.dev/)** — Next-generation frontend build tool
- **[Tailwind CSS 3.4](https://tailwindcss.com/)** — Utility-first CSS framework
- **[Axios](https://axios-http.com/)** — Promise-based HTTP client
- **[Lucide React](https://lucide.dev/)** — Beautiful & consistent icons

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Installation |
|-------------|---------|--------------|
| **Python** | 3.8+ | [Download](https://python.org/downloads/) |
| **Node.js** | 18+ | [Download](https://nodejs.org/) |
| **npm** | 9+ | Included with Node.js |
| **Google Gemini API Key** | — | [Get API Key](https://makersuite.google.com/app/apikey) |

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone [https://github.com/SoroushRF/Pareto.git](https://github.com/SoroushRF/Pareto.git)
cd Pareto
