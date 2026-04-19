# lizzarrd_ahhh

Submission repository for **DataHacks 2026**.

This project combines work from two tracks:

- **Economics Track** — developing and testing quantitative trading strategies for prediction markets  
- **Product & Entrepreneurship Track** — building a beginner-friendly web app that makes strategy tuning and backtesting accessible to non-technical users  

---

## 🚀 Overview

We built a trading system around Polymarket-style crypto prediction markets, focusing on BTC directional markets.

Our system has two layers:

1. **Technical Strategy Layer** — for developing and optimizing trading logic  
2. **Web Application Layer** — for making strategy tuning accessible to beginners  

The goal is to make quantitative trading more approachable while still using real data and realistic backtesting.

---

## 🧠 What This Project Does

Users can:

- Adjust trading strategy parameters  
- Run backtests on historical data  
- Analyze performance metrics (P&L, Sharpe, drawdown)  
- Visualize how asset prices change over time  

---

## 📁 Repository Contents

This repository contains strategy development files:

- `grok_strategy_ver2.py`
- `grok_strategy_ver3.py`
- `optimize_grok3.py`
- `strategy_3.py`

These represent different iterations of our trading strategy.

---

## ⚙️ Strategy Idea

Our strategy focuses on short-term crypto prediction markets using:

- price momentum  
- timing windows  
- entry and exit thresholds  
- parameter optimization  

The full version is designed for performance, while the web app version is simplified for faster runtime and better user experience.

---

## 🌐 Product Vision

Most trading tools assume users already understand quantitative finance.

We built a system that allows beginners to:

- experiment with strategies  
- learn through interaction  
- understand results through explanations and visualization  

---

## 💡 Why We Built This

We wanted to bridge the gap between:

- powerful but complex trading systems  
- simple but limited educational tools  

Our solution combines both into one system.

---

## 🛠️ Tech Direction

- Python (strategy + backend)
- FastAPI
- Pandas / NumPy
- React / Next.js
- Tailwind CSS

---

## 🌐 Running the Web App Locally

Follow these steps to run the full application.

---

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
