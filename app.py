"""
app.py — Flask Web Application for MHT-CET College Recommendation System.

Serves a multi-page web application with:
- Futuristic animated landing page
- Student authentication (login/signup)
- ML-powered college recommendations
- Server-persisted wishlist
- Side-by-side college comparison
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
import sys
import secrets

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from recommendation_engine import (
    get_recommendations, get_branch_groups, get_cities,
    get_db_stats, get_college_list, compare_colleges,
    get_college_branches
)
from data_utils import get_all_branch_groups, CATEGORY_MAP
from auth import (
    init_auth_tables, register_user, authenticate_user,
    get_user_by_id, login_required, api_login_required,
    add_to_wishlist, get_user_wishlist, remove_from_wishlist
)

app = Flask(__name__,
            template_folder=os.path.join(PROJECT_DIR, 'templates'),
            static_folder=os.path.join(PROJECT_DIR, 'static'))

app.secret_key = secrets.token_hex(32)

# Initialize auth tables on startup
init_auth_tables()


# ─── Public Page Routes ──────────────────────────────

@app.route('/')
def landing():
    """Serve the futuristic landing page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/login')
def login_page():
    """Serve the login page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/signup')
def signup_page():
    """Serve the signup page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    """Clear session and redirect to landing."""
    session.clear()
    return redirect(url_for('landing'))


# ─── Protected Page Routes ───────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    """Serve the main app dashboard (requires login)."""
    user = get_user_by_id(session['user_id'])
    return render_template('dashboard.html', user=user)


# ─── Auth API Routes ─────────────────────────────────

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """Register a new student account."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')

    if password != confirm:
        return jsonify({'error': 'Passwords do not match'}), 400

    success, message, user_id = register_user(name, email, password)

    if success:
        session['user_id'] = user_id
        session['user_name'] = name
        return jsonify({'success': True, 'message': message, 'redirect': '/dashboard'})
    else:
        return jsonify({'error': message}), 400


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Authenticate a student."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')

    success, message, user = authenticate_user(email, password)

    if success:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        return jsonify({'success': True, 'message': message, 'redirect': '/dashboard'})
    else:
        return jsonify({'error': message}), 401


# ─── Data API Routes ─────────────────────────────────

@app.route('/api/branches')
@api_login_required
def api_branches():
    """Return list of branch groups for the dropdown."""
    groups = get_branch_groups()
    return jsonify({'branches': groups})


@app.route('/api/cities')
@api_login_required
def api_cities():
    """Return list of cities for the dropdown."""
    cities = get_cities()
    return jsonify({'cities': cities})


@app.route('/api/categories')
@api_login_required
def api_categories():
    """Return list of user-friendly categories."""
    categories = list(CATEGORY_MAP.keys())
    return jsonify({'categories': categories})


@app.route('/api/colleges')
@api_login_required
def api_colleges():
    """Return list of all college names (for comparison search)."""
    colleges = get_college_list()
    return jsonify({'colleges': colleges})


@app.route('/api/stats')
@api_login_required
def api_stats():
    """Return database statistics."""
    stats = get_db_stats()
    return jsonify(stats)


@app.route('/api/recommend', methods=['POST'])
@api_login_required
def api_recommend():
    """Accept user input and return ranked recommendations."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No input provided'}), 400

    percentile = float(data.get('percentile', 50))
    category = data.get('category', 'OPEN')
    branch = data.get('branch', 'Any')
    city = data.get('city', None)
    tfws = bool(data.get('tfws', False))
    college_type = data.get('college_type', 'Any')

    if percentile < 0 or percentile > 100:
        return jsonify({'error': 'Percentile must be between 0 and 100'}), 400

    try:
        result = get_recommendations(
            percentile=percentile,
            category=category,
            branch_group=branch,
            city=city if city and city != 'Any' else None,
            tfws=tfws,
            college_type=college_type if college_type and college_type != 'Any' else None,
            top_n=15
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/college/<path:college_name>/branches')
@api_login_required
def api_college_branches(college_name):
    """Return all branch data for a specific college."""
    df = get_college_branches(college_name)
    if df.empty:
        return jsonify({'error': 'College not found', 'branches': []}), 404

    branches = []
    for _, row in df.iterrows():
        branches.append({
            'branch_name': row['Branch_Name'],
            'branch_group': row['Branch_Group'],
            'category': row['Category'],
            'score': round(float(row['Score']), 4) if row['Score'] else None,
            'rank': int(row['Rank']) if row['Rank'] else None,
            'is_tfws': bool(row['Is_TFWS']),
        })

    return jsonify({
        'college_name': college_name,
        'city': df['City'].iloc[0],
        'status': df['Status'].iloc[0],
        'total_branches': df['Branch_Group'].nunique(),
        'branches': branches
    })


@app.route('/api/compare')
@api_login_required
def api_compare():
    """Compare two colleges side by side."""
    c1 = request.args.get('c1', '')
    c2 = request.args.get('c2', '')

    if not c1 or not c2:
        return jsonify({'error': 'Both c1 and c2 college names are required'}), 400

    result = compare_colleges(c1, c2)
    return jsonify(result)


# ─── Wishlist API Routes ─────────────────────────────

@app.route('/api/wishlist', methods=['GET'])
@api_login_required
def api_get_wishlist():
    """Get current user's wishlist."""
    items = get_user_wishlist(session['user_id'])
    return jsonify({'wishlist': items})


@app.route('/api/wishlist', methods=['POST'])
@api_login_required
def api_add_wishlist():
    """Add a college to the current user's wishlist."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    success = add_to_wishlist(session['user_id'], data)
    if success:
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    else:
        return jsonify({'success': False, 'message': 'Already in wishlist'}), 200


@app.route('/api/wishlist/<int:item_id>', methods=['DELETE'])
@api_login_required
def api_remove_wishlist(item_id):
    """Remove an item from the current user's wishlist."""
    success = remove_from_wishlist(session['user_id'], item_id)
    if success:
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    else:
        return jsonify({'error': 'Item not found'}), 404


# ─── Run ──────────────────────────────────────────────

if __name__ == '__main__':
    print("\n  MHT-CET College Recommendation System")
    print("  Starting Flask server on http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
