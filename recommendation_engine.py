"""
recommendation_engine.py — Core recommendation logic.

Pipeline: SQL Coarse Filter → ML Scoring → Rank & Classify

This module connects:
1. SQLite for initial filtering (percentile range, category, branch, city, TFWS)
2. ML model for admission probability scoring
3. Aggregation and tier classification (Safe / Moderate / Dream)
"""

import sqlite3
import pandas as pd
import numpy as np
import joblib
import os

from data_utils import (
    get_category_codes, get_branch_group, get_branches_in_group,
    BRANCH_GROUPS, CATEGORY_MAP, classify_tier, tier_color
)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, 'college_data.db')
MODEL_PATH = os.path.join(PROJECT_DIR, 'ml_model.joblib')

# ─── Model Loading ───────────────────────────────────────────────

_model_cache = {}

def load_model():
    """Load ML model and artifacts (cached)."""
    if 'model' not in _model_cache:
        data = joblib.load(MODEL_PATH)
        _model_cache['model'] = data['model']
        _model_cache['encoders'] = data['encoders']
        _model_cache['scaler'] = data['scaler']
        _model_cache['feature_cols'] = data['feature_cols']
    return (
        _model_cache['model'],
        _model_cache['encoders'],
        _model_cache['scaler'],
        _model_cache['feature_cols']
    )


# ─── Step 1: SQL Coarse Filtering ────────────────────────────────

def sql_coarse_filter(percentile, category, branch_group, city=None, tfws=False,
                      college_type=None, percentile_range=5):
    """
    Use SQL to reduce the search space from ~18,000 to ~70-80 candidates.

    - Applies percentile range (±percentile_range)
    - Filters by category codes
    - Filters by branch group (all sub-branches)
    - Optionally filters by city, TFWS, and college type
    """
    conn = sqlite3.connect(DB_PATH)

    score_low = max(0, percentile - percentile_range)
    score_high = min(100, percentile + percentile_range)

    # Build query
    query = "SELECT * FROM cutoffs WHERE Score BETWEEN ? AND ?"
    params = [score_low, score_high]

    # Category filter — map user-friendly name to all raw codes
    if category and category.upper() != 'ANY':
        if tfws:
            cat_codes = get_category_codes(category) + ['TFWS']
        else:
            cat_codes = get_category_codes(category)

        placeholders = ','.join(['?' for _ in cat_codes])
        query += f" AND Category IN ({placeholders})"
        params.extend(cat_codes)
    elif tfws:
        query += " AND Is_TFWS = 1"

    # Branch filter
    if branch_group and branch_group != 'Any':
        sub_branches = get_branches_in_group(branch_group)
        all_branch_names = sub_branches + [branch_group]
        placeholders = ','.join(['?' for _ in all_branch_names])
        query += f" AND (Branch_Group IN ({placeholders}) OR Branch_Name IN ({placeholders}))"
        params.extend(all_branch_names * 2)

    # City filter
    if city and city != 'Any' and city != '':
        query += " AND City LIKE ?"
        params.append(f"%{city}%")

    # College type filter (matches against Status column)
    if college_type:
        query += " AND Status LIKE ?"
        params.append(f"%{college_type}%")

    query += " ORDER BY Score DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df


# ─── Step 2: ML Scoring ──────────────────────────────────────────

def ml_score_candidates(candidates_df, user_percentile):
    """
    Apply ML model to each candidate row and compute admission probability.

    Returns the DataFrame with added 'Probability' column.
    """
    if candidates_df.empty:
        candidates_df['Probability'] = []
        return candidates_df

    model, encoders, scaler, feature_cols = load_model()

    # Prepare features
    df = candidates_df.copy()
    df['User_Percentile'] = user_percentile
    df['Percentile_Diff'] = user_percentile - df['Score']

    # Encode categorical variables
    for col in ['Branch_Group', 'Category', 'City']:
        le = encoders[col]
        # Handle unseen labels by mapping to a default
        df[f'{col}_Encoded'] = df[col].apply(
            lambda x: le.transform([x])[0] if x in le.classes_ else -1
        )

    # Normalize Score and User_Percentile
    score_pct_values = df[['Score', 'User_Percentile']].values
    normalized = scaler.transform(score_pct_values)
    df['Score_Norm'] = normalized[:, 0]
    df['UserPct_Norm'] = normalized[:, 1]

    # Build feature matrix
    X = df[feature_cols].fillna(-1)

    # Predict probabilities
    probabilities = model.predict_proba(X)[:, 1]
    df['Probability'] = probabilities

    return df


# ─── Step 3: Rank & Classify ─────────────────────────────────────

def rank_and_classify(scored_df, top_n=15):
    """
    Sort by probability descending and classify into tiers.

    Returns a list of recommendation dicts ready for JSON serialization.
    """
    if scored_df.empty:
        return []

    # De-duplicate: keep highest probability per college-branch combo
    scored_df = scored_df.sort_values('Probability', ascending=False)
    scored_df = scored_df.drop_duplicates(subset=['College_Name', 'Branch_Group'], keep='first')

    # Take top N
    top = scored_df.head(top_n)

    recommendations = []
    for rank, (_, row) in enumerate(top.iterrows(), 1):
        prob = float(row['Probability'])
        tier = classify_tier(prob)
        recommendations.append({
            'rank': rank,
            'college_name': row['College_Name'],
            'branch_name': row.get('Branch_Name', row['Branch_Group']),
            'branch_group': row['Branch_Group'],
            'category': row['Category'],
            'city': row['City'],
            'cutoff_score': round(float(row['Score']), 4),
            'probability': round(prob, 4),
            'probability_pct': round(prob * 100, 1),
            'tier': tier,
            'tier_color': tier_color(tier),
            'college_id': int(row['College_ID']) if pd.notna(row['College_ID']) else None,
            'branch_id': int(row['Branch_ID']) if pd.notna(row['Branch_ID']) else None,
        })

    return recommendations


# ─── Master Function ─────────────────────────────────────────────

def get_recommendations(percentile, category, branch_group, city=None, tfws=False,
                        college_type=None, percentile_range=5, top_n=15):
    """
    Full pipeline: SQL Filter → ML Score → Rank & Classify.

    Args:
        percentile: User's CET percentile (0-100)
        category: User's category (OPEN, OBC, SC, ST, etc.)
        branch_group: Preferred branch group name
        city: Preferred city (optional)
        tfws: Whether user is TFWS eligible
        college_type: College type filter (Government, Un-Aided, etc.)
        percentile_range: ± range for SQL filtering (default 5)
        top_n: Number of recommendations to return

    Returns:
        dict with 'recommendations', 'stats', and 'filters_applied'
    """
    # Step 1: SQL Coarse Filter
    candidates = sql_coarse_filter(
        percentile, category, branch_group, city, tfws, college_type, percentile_range
    )

    # If too few results, widen the range
    if len(candidates) < 10 and percentile_range < 15:
        candidates = sql_coarse_filter(
            percentile, category, branch_group, city, tfws, college_type,
            percentile_range=percentile_range + 5
        )

    # Step 2: ML Scoring
    scored = ml_score_candidates(candidates, percentile)

    # Step 3: Rank & Classify
    recommendations = rank_and_classify(scored, top_n)

    # Stats
    tier_counts = {'Safe': 0, 'Moderate': 0, 'Dream': 0}
    for rec in recommendations:
        tier_counts[rec['tier']] = tier_counts.get(rec['tier'], 0) + 1

    return {
        'recommendations': recommendations,
        'stats': {
            'total_candidates_filtered': len(candidates),
            'total_recommendations': len(recommendations),
            'tier_counts': tier_counts,
        },
        'filters_applied': {
            'percentile': percentile,
            'category': category,
            'branch_group': branch_group,
            'city': city or 'Any',
            'tfws': tfws,
            'college_type': college_type or 'Any',
            'percentile_range': percentile_range,
        }
    }


# ─── Comparison & Wishlist Helpers ────────────────────────────────

def get_college_branches(college_name):
    """Get all branch cutoff data for a specific college."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT College_Name, Branch_Name, Branch_Group, Category, City,
               Score, Rank, Is_TFWS, Status, Level
        FROM cutoffs
        WHERE College_Name = ?
        ORDER BY Branch_Group, Category, Score DESC
    """
    df = pd.read_sql_query(query, conn, params=[college_name])
    conn.close()
    return df


def compare_colleges(college1, college2):
    """
    Compare two colleges side-by-side.
    Returns merged branch data showing cutoff differences.
    """
    df1 = get_college_branches(college1)
    df2 = get_college_branches(college2)

    if df1.empty or df2.empty:
        return {'error': 'One or both colleges not found', 'college1': [], 'college2': []}

    # Get all branches for each college, aggregated
    def aggregate_branches(df, prefix):
        agg = df.groupby(['Branch_Group', 'Category']).agg(
            Score=('Score', 'max'),
            Rank=('Rank', 'min'),
            Branch_Name=('Branch_Name', 'first')
        ).reset_index()
        return agg

    agg1 = aggregate_branches(df1, 'c1')
    agg2 = aggregate_branches(df2, 'c2')

    # Get common branches
    branches1 = set(df1['Branch_Group'].unique())
    branches2 = set(df2['Branch_Group'].unique())
    common_branches = sorted(branches1 & branches2)
    only_in_1 = sorted(branches1 - branches2)
    only_in_2 = sorted(branches2 - branches1)

    # Build comparison data for common branches
    comparison = []
    for branch in common_branches:
        b1 = agg1[agg1['Branch_Group'] == branch]
        b2 = agg2[agg2['Branch_Group'] == branch]

        # Get common categories
        cats1 = set(b1['Category'].unique())
        cats2 = set(b2['Category'].unique())
        all_cats = sorted(cats1 | cats2)

        for cat in all_cats:
            row1 = b1[b1['Category'] == cat]
            row2 = b2[b2['Category'] == cat]

            score1 = float(row1['Score'].values[0]) if not row1.empty else None
            score2 = float(row2['Score'].values[0]) if not row2.empty else None

            diff = None
            if score1 is not None and score2 is not None:
                diff = round(score1 - score2, 4)

            comparison.append({
                'branch_group': branch,
                'category': cat,
                'college1_score': round(score1, 4) if score1 else None,
                'college2_score': round(score2, 4) if score2 else None,
                'difference': diff,
                'easier_in': 'college1' if diff and diff < 0 else ('college2' if diff and diff > 0 else 'same')
            })

    return {
        'college1': {
            'name': college1,
            'city': df1['City'].iloc[0] if not df1.empty else '',
            'total_branches': len(branches1),
            'status': df1['Status'].iloc[0] if not df1.empty else '',
        },
        'college2': {
            'name': college2,
            'city': df2['City'].iloc[0] if not df2.empty else '',
            'total_branches': len(branches2),
            'status': df2['Status'].iloc[0] if not df2.empty else '',
        },
        'comparison': comparison,
        'common_branches': common_branches,
        'only_in_college1': only_in_1,
        'only_in_college2': only_in_2,
    }


def get_college_list():
    """Get list of all unique college names for dropdowns."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT College_Name, City FROM cutoffs ORDER BY College_Name")
    colleges = [{'name': r[0], 'city': r[1]} for r in cursor.fetchall()]
    conn.close()
    return colleges


def get_db_stats():
    """Get database statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stats = {}
    cursor.execute("SELECT COUNT(*) FROM cutoffs")
    stats['total_records'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT College_Name) FROM cutoffs")
    stats['total_colleges'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT Branch_Group) FROM cutoffs")
    stats['total_branches'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT City) FROM cutoffs WHERE City != 'Unknown'")
    stats['total_cities'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT Category) FROM cutoffs")
    stats['total_categories'] = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(Score), MAX(Score), AVG(Score) FROM cutoffs WHERE Score > 0")
    row = cursor.fetchone()
    stats['score_min'] = round(row[0], 2)
    stats['score_max'] = round(row[1], 2)
    stats['score_avg'] = round(row[2], 2)

    conn.close()
    return stats


def get_cities():
    """Get sorted list of cities."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT City FROM cutoffs WHERE City != 'Unknown' ORDER BY City")
    cities = [r[0] for r in cursor.fetchall()]
    conn.close()
    return cities


def get_branch_groups():
    """Get sorted list of branch groups from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Branch_Group FROM cutoffs ORDER BY Branch_Group")
    groups = [r[0] for r in cursor.fetchall()]
    conn.close()
    return groups
