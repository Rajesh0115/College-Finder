# 🎓 MHT-CET College Finder

An ML-powered college recommendation system for MHT-CET admissions in Maharashtra, India. Built with Flask and a futuristic sci-fi themed UI.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-green?logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-orange?logo=scikit-learn&logoColor=white)

---

## ✨ Features

- **ML-Powered Recommendations** — Uses a trained Random Forest model to score and rank colleges into Safe, Moderate, and Dream categories
- **Smart Filtering** — Filter by percentile, category (OPEN, OBC, SC, ST, etc.), branch, city, TFWS, and college type
- **Futuristic UI** — Immersive sci-fi command center interface with glassmorphism, holographic 3D cards, and dynamic animations
- **Student Authentication** — Secure login/signup system with session management
- **Wishlist** — Save and manage your favorite colleges
- **College Comparison** — Compare two colleges side-by-side
- **Database Stats** — View real-time statistics of the college database

## 🛠️ Tech Stack

| Layer       | Technology                    |
|-------------|-------------------------------|
| Backend     | Python, Flask                 |
| ML Engine   | scikit-learn, pandas, numpy   |
| Database    | SQLite                        |
| Frontend    | HTML5, CSS3, JavaScript       |
| UI Design   | Glassmorphism, CSS Animations |

## 📁 Project Structure

```
College Finder/
├── app.py                    # Flask web server & API routes
├── auth.py                   # Authentication system (login/signup/sessions)
├── recommendation_engine.py  # ML recommendation logic
├── data_utils.py             # Data processing utilities
├── database_setup.py         # SQLite database initialization
├── train_ml_model.py         # ML model training script
├── plumber2.py               # Data pipeline utilities
├── run_setup.py              # Setup script to initialize the app
├── requirements.txt          # Python dependencies
├── templates/
│   ├── landing.html          # Futuristic landing page
│   ├── login.html            # Login page
│   ├── signup.html           # Signup page
│   ├── dashboard.html        # Main recommendation dashboard
│   └── index.html            # Legacy index page
├── static/
│   ├── style.css             # Main dashboard styles
│   ├── script.js             # Dashboard interactivity
│   ├── landing.css           # Landing page styles
│   ├── landing.js            # Landing page animations
│   ├── auth.css              # Auth page styles
│   └── auth.js               # Auth page logic
└── collegepune/              # Data files (not included — see below)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/College-Finder.git
   cd College-Finder
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   source .venv/bin/activate # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   ```bash
   python run_setup.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   Navigate to `http://localhost:5000`

## 📊 Data Files

The `collegepune/` directory contains MHT-CET cutoff data (2022–2025) and trained ML models. These files are **not included** in the repository due to their large size (~300MB+).

To get the data:
- Contact the repository owner
- Or prepare your own cutoff CSV files and run `python train_ml_model.py`

## 📸 Screenshots

_Coming soon_

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">Made with ❤️ for MHT-CET aspirants</p>
