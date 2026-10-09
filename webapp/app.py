"""Mise - local web UI for the Yelp -> Postgres ETL pipeline.

Wraps the existing project modules (BusinessSearch, DatabaseDriver, queries) in a
Flask app so searches can be run and the loaded table browsed from the browser.

Run:  ./run_web.sh      then open http://127.0.0.1:5055
"""
import configparser
import json
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from flask import Flask, jsonify, redirect, render_template, request as flask_request, url_for

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import request as project_request  # noqa: E402  (project module, needs PROJECT_DIR on path)
from auth import headers  # noqa: E402
from businesssearch import BusinessSearch  # noqa: E402
from databasedriver import DatabaseDriver  # noqa: E402
from driver import to_string  # noqa: E402
from queries import insert_business_table  # noqa: E402

SEARCH_URL = 'https://api.yelp.com/v3/businesses/search'
SAMPLE_FILE = Path(__file__).resolve().parent / 'sample_businesses.json'

config = configparser.ConfigParser()
config.read_file(open(PROJECT_DIR / 'config.cfg'))

app = Flask(__name__)


def api_key_configured():
    """Yelp requires a 128-char key; anything else will be rejected with a 400."""
    key = config['KEYS'].get('API_KEY', '').strip()
    return len(key) == 128


def db_connection():
    return psycopg2.connect(
        "host={} dbname={} user={} password={} port={}".format(*config['DATABASE'].values())
    )


def fetch_live(term, location, price):
    """Call the Yelp API directly so HTTP failures can be reported in the UI."""
    params = {'term': term, 'location': location}
    if price:
        params['price'] = price
    try:
        response = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
    except requests.RequestException as exc:
        return None, f"Could not reach the Yelp API: {exc}"

    if response.status_code == 200:
        return json.loads(response.content), None

    detail = ''
    try:
        error = response.json().get('error', {})
        detail = error.get('description') or error.get('code', '')
    except ValueError:
        detail = response.text[:200]
    return None, f"Yelp returned {response.status_code}. {detail}"


def fetch_sample(term):
    """Offline payload shaped like a Yelp response, loosely filtered by search term."""
    payload = json.loads(SAMPLE_FILE.read_text())
    businesses = payload['businesses']
    if term:
        needle = term.lower()
        matched = [
            b for b in businesses
            if needle in b['name'].lower()
            or any(needle in c['title'].lower() for c in b.get('categories', []))
        ]
        if matched:
            businesses = matched
    return {'businesses': businesses}


def run_etl(term, location, price, source):
    """Fetch, parse and upsert through the project's own classes. Returns (count, error)."""
    if source == 'live':
        payload, error = fetch_live(term, location, price)
        if error:
            return 0, error
    else:
        payload = fetch_sample(term)

    # BusinessSearch does its own fetch via Request.get_content; hand it the payload
    # we already have so parsing stays the project's code.
    original = project_request.Request.get_content
    project_request.Request.get_content = staticmethod(lambda url, param: payload)
    try:
        results = BusinessSearch(term=term, location=location, price=price).get_results()
    finally:
        project_request.Request.get_content = original

    if not results:
        return 0, None

    db = DatabaseDriver()
    try:
        db.setup()
        queries = [insert_business_table.format(*to_string(r)) for r in results]
        db.execute_query("BEGIN; \n" + '\n'.join(queries) + "\nCOMMIT;")
    finally:
        db._conn.close()
    return len(results), None


def load_rows():
    with db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT business_id, business_name, image_url, url, review_count, categories,
                       rating, latitude, longitude, price, location, phone
                FROM yelp.business
                ORDER BY rating DESC NULLS LAST, review_count DESC
            """)
            return [dict(row) for row in cur.fetchall()]


def summarise(rows):
    rated = [r['rating'] for r in rows if r['rating'] is not None]
    categories = {c for r in rows for c in (r['categories'] or '').split() if c}
    return {
        'total': len(rows),
        'avg_rating': round(sum(rated) / len(rated), 2) if rated else None,
        'reviews': sum(r['review_count'] or 0 for r in rows),
        'categories': len(categories),
        'with_coords': sum(1 for r in rows if r['latitude'] is not None),
    }


@app.route('/')
def index():
    try:
        rows = load_rows()
        db_error = None
    except psycopg2.Error as exc:
        rows, db_error = [], str(exc).strip()

    return render_template(
        'index.html',
        rows=rows,
        stats=summarise(rows),
        db_error=db_error,
        key_ready=api_key_configured(),
        database=config['DATABASE']['database'],
        term=flask_request.args.get('term', 'food'),
        location=flask_request.args.get('location', 'Montreal'),
        price=flask_request.args.get('price', '4'),
        source=flask_request.args.get('source', 'live' if api_key_configured() else 'sample'),
        message=flask_request.args.get('message'),
        error=flask_request.args.get('error'),
    )


@app.route('/search', methods=['POST'])
def search():
    term = flask_request.form.get('term', '').strip() or 'food'
    location = flask_request.form.get('location', '').strip() or 'Montreal'
    price = flask_request.form.get('price', '').strip()
    source = flask_request.form.get('source', 'sample')

    params = {'term': term, 'location': location, 'price': price, 'source': source}
    try:
        count, error = run_etl(term, location, int(price) if price else None, source)
    except (psycopg2.Error, KeyError, ValueError) as exc:
        return redirect(url_for('index', error=f"{type(exc).__name__}: {exc}", **params))

    if error:
        return redirect(url_for('index', error=error, **params))
    label = 'Yelp API' if source == 'live' else 'sample data'
    if count:
        params['message'] = f"Loaded {count} businesses from {label} for '{term}' in {location}."
    else:
        params['message'] = f"No businesses returned from {label} for '{term}' in {location}."
    return redirect(url_for('index', **params))


@app.route('/clear', methods=['POST'])
def clear():
    try:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE yelp.business")
        return redirect(url_for('index', message='Table yelp.business emptied.'))
    except psycopg2.Error as exc:
        return redirect(url_for('index', error=str(exc).strip()))


@app.route('/api/businesses')
def api_businesses():
    """Used by the map; also handy for checking the load from the command line."""
    rows = load_rows()
    return jsonify({'count': len(rows), 'businesses': rows})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5055, debug=False)
