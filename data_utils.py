"""
data_utils.py — Utility functions for MHT-CET College Recommendation System
Handles category mapping, city normalization, and branch grouping.
"""

import re

# ──────────────────────────────────────────────────
# CATEGORY MAPPING
# Maps user-friendly category names to all matching
# raw category codes found in the MHT-CET data.
# G = General, L = Linguistic minority, DEF = Defence, PWD = Disability
# Suffix: S = State, H = Home Univ, O = Other Univ
# ──────────────────────────────────────────────────

CATEGORY_MAP = {
    "OPEN": ["GOPENS", "GOPENH", "GOPENO", "LOPENS", "LOPENH", "LOPENO", "DEFOPENS", "PWDOPENS", "PWDOPENH"],
    "OBC":  ["GOBCS", "GOBCH", "GOBCO", "LOBCS", "LOBCH", "LOBCO", "DEFOBCS", "DEFROBCS", "PWDOBCS", "PWDOBCH", "PWDROBC"],
    "SC":   ["GSCS", "GSCH", "GSCO", "LSCS", "LSCH", "LSCO", "DEFSCS", "DEFRSCS", "PWDSCS", "PWDSCH", "PWDRSCS", "PWDRSCH"],
    "ST":   ["GSTS", "GSTH", "GSTO", "LSTS", "LSTH", "LSTO"],
    "VJ":   ["GVJS", "GVJH", "GVJO", "LVJS", "LVJH", "LVJO"],
    "NT1":  ["GNT1S", "GNT1H", "GNT1O", "LNT1S", "LNT1H"],
    "NT2":  ["GNT2S", "GNT2H", "GNT2O", "LNT2S", "LNT2H", "LNT2O"],
    "NT3":  ["GNT3S", "GNT3H", "GNT3O", "LNT3S", "LNT3H", "LNT3O", "DEFRNT3S", "PWDRNT3S"],
    "EWS":  ["EWS"],
    "TFWS": ["TFWS"],
}

# Reverse map: raw code → user-friendly name
REVERSE_CATEGORY_MAP = {}
for friendly, codes in CATEGORY_MAP.items():
    for code in codes:
        REVERSE_CATEGORY_MAP[code] = friendly


def get_category_codes(user_category: str) -> list:
    """Given a user-friendly category like 'OBC', return all matching raw codes."""
    key = user_category.upper().strip()
    return CATEGORY_MAP.get(key, [key])


def get_friendly_category(raw_code: str) -> str:
    """Given a raw code like 'GOBCS', return 'OBC'."""
    return REVERSE_CATEGORY_MAP.get(raw_code, raw_code)


# ──────────────────────────────────────────────────
# CITY NORMALIZATION
# The extracted cities from PDF data are messy —
# some are zip codes, institution names, etc.
# ──────────────────────────────────────────────────

# Known bad city values that should be cleaned
CITY_CORRECTIONS = {
    "444302": "Amravati",
    "(Nashik)": "Nashik",
    "Ahmednagar.": "Ahmednagar",
    "Dist Thane": "Thane",
    "Dist Wardha": "Wardha",
    "Dist. Nandurbar": "Nandurbar",
    "Badlapur(W)": "Badlapur",
    "Baramati Dist.Pune": "Baramati",
    "Barshi": "Barshi",
    "Bapsai Tal.Kalyan": "Kalyan",
    "Agaskhind Tal. Sinnar": "Sinnar",
    "Adgaon Nashik": "Nashik",
    "Bota Sangamner": "Sangamner",
    "Chas Dist. Ahmednagar": "Ahmednagar",
    "Chincholi Dist. Nashik": "Nashik",
    "Avasari Khurd": "Pune",
}

# Values that are clearly not city names (institution names, etc.)
BAD_CITY_PATTERNS = [
    r"institute",
    r"college",
    r"group of",
    r"technology",
    r"engineering",
    r"research",
    r"education",
    r"foundation",
    r"polytechnic",
    r"society",
    r"charitable",
    r"trust",
]


def normalize_city(city: str) -> str:
    """Clean and normalize city names."""
    if not city or not isinstance(city, str):
        return "Unknown"

    city = city.strip()

    # Direct corrections
    if city in CITY_CORRECTIONS:
        return CITY_CORRECTIONS[city]

    # Check for bad patterns (institution names parsed as cities)
    city_lower = city.lower()
    for pattern in BAD_CITY_PATTERNS:
        if re.search(pattern, city_lower):
            return "Unknown"

    # Check if it's a numeric value (zip code)
    if re.match(r'^\d+$', city):
        return "Unknown"

    # Basic cleanup
    city = re.sub(r'\s+', ' ', city)
    city = city.strip('.')

    return city


# ──────────────────────────────────────────────────
# BRANCH NORMALIZATION / GROUPING
# Group similar branch names under parent categories
# ──────────────────────────────────────────────────

BRANCH_GROUPS = {
    "Computer Science and Engineering": [
        "Computer Engineering",
        "Computer Science and Engineering",
        "Computer Science and Engineering (Artificial Intelligence and Data Science)",
        "Computer Science and Engineering (Artificial Intelligence)",
        "Computer Science and Engineering (Cyber Security)",
        "Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain",
        "Computer Science and Engineering (IoT)",
        "Computer Science and Engineering(Artificial Intelligence and Machine Learning)",
        "Computer Science and Engineering(Cyber Security)",
        "Computer Science and Engineering(Data Science)",
        "Computer Science and Information Technology",
        "Computer Science and Technology",
        "Computer Technology",
        "Computer Engineering (Regional Language)",
        "Computer Science and Design",
        "Computer Science and Business Systems",
    ],
    "Information Technology": [
        "Information Technology",
    ],
    "Artificial Intelligence & Data Science": [
        "Artificial Intelligence",
        "Artificial Intelligence (AI) and Data Science",
        "Artificial Intelligence and Data Science",
        "Artificial Intelligence and Machine Learning",
        "Data Science",
        "Data Engineering",
    ],
    "Electronics & Telecommunication": [
        "Electronics and Telecommunication Engg",
        "Electronics and Telecommunication Engineering",
        "Electronics and Communication Engineering",
        "Electronics Engineering",
        "Electronics Engineering ( VLSI Design and Technology)",
        "Electronics and Computer Engineering",
        "Electronics and Computer Science",
    ],
    "Electrical Engineering": [
        "Electrical Engineering",
        "Electrical and Electronics Engineering",
        "Electrical and Computer",
        "Electrical Engg [Electrical and Power]",
        "Electrical Engg[Electronics and Power]",
    ],
    "Mechanical Engineering": [
        "Mechanical Engineering",
        "Mechanical Engineering (Sandwich)",
        "Mechatronics Engineering",
        "Automation and Robotics",
    ],
    "Civil Engineering": [
        "Civil Engineering",
        "Civil and Environmental Engineering",
        "Civil and infrastructure Engineering",
    ],
    "Chemical Engineering": [
        "Chemical Engineering",
        "Dyestuff Technology",
        "Petrochemical Technology",
        "Polymer Engineering and Technology",
        "Plastic and Polymer Technology",
        "Oil and Paints Technology",
        "Oil Technology",
        "Oils",
        "Paper and Pulp Technology",
        "Pharmaceutical Engineering and Technology",
        "Surface Coating Technology",
        "Textile Chemistry",
    ],
    "Cyber Security": [
        "Cyber Security",
    ],
    "Instrumentation Engineering": [
        "Instrumentation Engineering",
        "Instrumentation and Control Engineering",
    ],
    "Bio Technology": [
        "Bio Technology",
        "Bio Medical Engineering",
    ],
    "Automobile Engineering": [
        "Automobile Engineering",
        "Automotive Technology",
    ],
    "Aerospace Engineering": [
        "Aeronautical Engineering",
    ],
    "Agricultural Engineering": [
        "Agricultural Engineering",
        "Agriculture Engineering",
    ],
    "Production Engineering": [
        "Production Engineering",
        "Production Engineering (Sandwich)",
        "Manufacturing Engineering and Automation Technology",
    ],
    "Printing Technology": [
        "Printing Technology",
    ],
    "Fashion Technology": [
        "Fashion Technology",
        "Fibres and Textile Processing Technology",
        "Man Made Textile Technology",
        "Textile Engineering / Technology",
        "Textile Plant Engineering",
    ],
    "Mining Engineering": [
        "Mining Engineering",
        "Metallurgy and Material Technology",
    ],
    "Food Technology": [
        "Food Engineering and Technology",
        "Food Technology",
    ],
    "Robotics & AI": [
        "Robotics and Artificial Intelligence",
    ],
    "Internet of Things": [
        "Internet of Things (IoT)",
    ],
}

# Build reverse lookup: exact branch name → group name
BRANCH_TO_GROUP = {}
for group, branches in BRANCH_GROUPS.items():
    for branch in branches:
        BRANCH_TO_GROUP[branch.lower()] = group


def get_branch_group(branch_name: str) -> str:
    """Get the parent group for a branch name, or return as-is."""
    if not branch_name:
        return "Other"
    return BRANCH_TO_GROUP.get(branch_name.lower().strip(), branch_name)


def get_branches_in_group(group_name: str) -> list:
    """Get all branch name variants in a group."""
    return BRANCH_GROUPS.get(group_name, [group_name])


def get_all_branch_groups() -> list:
    """Get sorted list of all branch group names."""
    return sorted(BRANCH_GROUPS.keys())


# ──────────────────────────────────────────────────
# ADMISSION TIER CLASSIFICATION
# ──────────────────────────────────────────────────

def classify_tier(probability: float) -> str:
    """Classify admission chance into Safe / Moderate / Dream."""
    if probability >= 0.75:
        return "Safe"
    elif probability >= 0.45:
        return "Moderate"
    else:
        return "Dream"


def tier_color(tier: str) -> str:
    """Get the color associated with each tier."""
    return {
        "Safe": "#10b981",
        "Moderate": "#f59e0b",
        "Dream": "#ef4444",
    }.get(tier, "#6b7280")
