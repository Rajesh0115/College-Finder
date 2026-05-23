"""
database_setup.py - Creates SQLite database from enhanced CSV data.
"""
import sqlite3
import pandas as pd
import os
import re

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(PROJECT_DIR, 'collegepune', 'cutoff_2022_enhanced.csv')
DB_PATH = os.path.join(PROJECT_DIR, 'college_data.db')

CITY_CORRECTIONS = {
    "444302": "Amravati", "(Nashik)": "Nashik", "Ahmednagar.": "Ahmednagar",
    "Dist Thane": "Thane", "Dist Wardha": "Wardha", "Dist. Nandurbar": "Nandurbar",
    "Badlapur(W)": "Badlapur", "Baramati Dist.Pune": "Baramati",
    "Bapsai Tal.Kalyan": "Kalyan", "Agaskhind Tal. Sinnar": "Sinnar",
    "Adgaon Nashik": "Nashik", "Bota Sangamner": "Sangamner",
    "Chas Dist. Ahmednagar": "Ahmednagar", "Chincholi Dist. Nashik": "Nashik",
    "Avasari Khurd": "Pune",
}
BAD_PATTERNS = ["institute", "college", "group of", "technology",
                "engineering", "research", "education", "foundation",
                "polytechnic", "society", "charitable", "trust"]

def normalize_city(city):
    if not city or not isinstance(city, str):
        return "Unknown"
    city = city.strip()
    if city in CITY_CORRECTIONS:
        return CITY_CORRECTIONS[city]
    cl = city.lower()
    for p in BAD_PATTERNS:
        if p in cl:
            return "Unknown"
    if re.match(r'^\d+$', city):
        return "Unknown"
    return city.strip('.')

BRANCH_GROUPS = {
    "Computer Science and Engineering": [
        "Computer Engineering", "Computer Science and Engineering",
        "Computer Science and Engineering (Artificial Intelligence and Data Science)",
        "Computer Science and Engineering (Artificial Intelligence)",
        "Computer Science and Engineering (Cyber Security)",
        "Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain",
        "Computer Science and Engineering (IoT)",
        "Computer Science and Engineering(Artificial Intelligence and Machine Learning)",
        "Computer Science and Engineering(Cyber Security)",
        "Computer Science and Engineering(Data Science)",
        "Computer Science and Information Technology", "Computer Science and Technology",
        "Computer Technology", "Computer Engineering (Regional Language)",
        "Computer Science and Design", "Computer Science and Business Systems",
    ],
    "Information Technology": ["Information Technology"],
    "AI & Data Science": [
        "Artificial Intelligence", "Artificial Intelligence (AI) and Data Science",
        "Artificial Intelligence and Data Science", "Artificial Intelligence and Machine Learning",
        "Data Science", "Data Engineering",
    ],
    "Electronics & Telecom": [
        "Electronics and Telecommunication Engg", "Electronics and Telecommunication Engineering",
        "Electronics and Communication Engineering", "Electronics Engineering",
        "Electronics Engineering ( VLSI Design and Technology)",
        "Electronics and Computer Engineering", "Electronics and Computer Science",
    ],
    "Electrical Engineering": [
        "Electrical Engineering", "Electrical and Electronics Engineering",
        "Electrical and Computer", "Electrical Engg [Electrical and Power]",
        "Electrical Engg[Electronics and Power]",
    ],
    "Mechanical Engineering": [
        "Mechanical Engineering", "Mechanical Engineering (Sandwich)",
        "Mechatronics Engineering", "Automation and Robotics",
    ],
    "Civil Engineering": [
        "Civil Engineering", "Civil and Environmental Engineering",
        "Civil and infrastructure Engineering",
    ],
    "Chemical Engineering": [
        "Chemical Engineering", "Dyestuff Technology", "Petrochemical Technology",
        "Polymer Engineering and Technology", "Plastic and Polymer Technology",
        "Oil and Paints Technology", "Oil Technology", "Oils",
        "Paper and Pulp Technology", "Pharmaceutical Engineering and Technology",
        "Surface Coating Technology", "Textile Chemistry",
    ],
    "Cyber Security": ["Cyber Security"],
    "Instrumentation Engineering": [
        "Instrumentation Engineering", "Instrumentation and Control Engineering",
    ],
    "Bio Technology": ["Bio Technology", "Bio Medical Engineering"],
    "Automobile Engineering": ["Automobile Engineering", "Automotive Technology"],
    "Aerospace Engineering": ["Aeronautical Engineering"],
    "Agricultural Engineering": ["Agricultural Engineering", "Agriculture Engineering"],
    "Production Engineering": [
        "Production Engineering", "Production Engineering (Sandwich)",
        "Manufacturing Engineering and Automation Technology",
    ],
    "Printing Technology": ["Printing Technology"],
    "Textile Technology": [
        "Fashion Technology", "Fibres and Textile Processing Technology",
        "Man Made Textile Technology", "Textile Engineering / Technology", "Textile Plant Engineering",
    ],
    "Mining & Metallurgy": ["Mining Engineering", "Metallurgy and Material Technology"],
    "Food Technology": ["Food Engineering and Technology", "Food Technology"],
    "Robotics & AI": ["Robotics and Artificial Intelligence"],
    "Internet of Things": ["Internet of Things (IoT)"],
}

BRANCH_TO_GROUP = {}
for grp, branches in BRANCH_GROUPS.items():
    for b in branches:
        BRANCH_TO_GROUP[b.lower()] = grp

def get_branch_group(bn):
    if not bn or not isinstance(bn, str):
        return "Other"
    return BRANCH_TO_GROUP.get(bn.lower().strip(), bn)

def extract_id(val):
    if pd.isna(val):
        return None
    m = re.match(r'^(\d+)\s+-', str(val))
    if m:
        return int(m.group(1))
    return None


def create_database():
    print("Loading CSV from:", CSV_PATH)
    df = pd.read_csv(CSV_PATH)
    print("Loaded", len(df), "rows")

    df['City_Clean'] = df['City'].apply(normalize_city)
    df['Branch_Group'] = df['Branch_Name'].apply(get_branch_group)
    df['Is_TFWS'] = (df['Category'] == 'TFWS').astype(int)

    if 'College_ID' not in df.columns:
        df['College_ID'] = df['College'].apply(extract_id)
    if 'Branch_ID' not in df.columns:
        df['Branch_ID'] = df['Branch'].apply(extract_id)

    df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
    df['Rank'] = pd.to_numeric(df['Rank'], errors='coerce')
    df_valid = df.dropna(subset=['Score']).copy()
    print("Valid rows:", len(df_valid))

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    db_df = df_valid[[
        'College_Name', 'Branch_Name', 'Category', 'City_Clean',
        'Status', 'Level', 'Stage', 'Score', 'Rank',
        'Branch_Group', 'Is_TFWS', 'College_ID', 'Branch_ID'
    ]].rename(columns={'City_Clean': 'City'})
    db_df.to_sql('cutoffs', conn, index=False, if_exists='replace')

    cursor = conn.cursor()
    for idx_sql in [
        "CREATE INDEX idx_score ON cutoffs(Score)",
        "CREATE INDEX idx_category ON cutoffs(Category)",
        "CREATE INDEX idx_city ON cutoffs(City)",
        "CREATE INDEX idx_branch_group ON cutoffs(Branch_Group)",
        "CREATE INDEX idx_tfws ON cutoffs(Is_TFWS)",
        "CREATE INDEX idx_college_id ON cutoffs(College_ID)",
        "CREATE INDEX idx_branch_id ON cutoffs(Branch_ID)",
    ]:
        cursor.execute(idx_sql)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM cutoffs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT College_Name) FROM cutoffs")
    colleges = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT Branch_Group) FROM cutoffs")
    groups = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT City) FROM cutoffs WHERE City != 'Unknown'")
    cities = cursor.fetchone()[0]
    conn.close()

    print("DB created:", DB_PATH)
    print("Records:", total, "| Colleges:", colleges, "| Groups:", groups, "| Cities:", cities)
    return DB_PATH


if __name__ == '__main__':
    create_database()
