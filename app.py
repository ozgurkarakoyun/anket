# -*- coding: utf-8 -*-
"""
FJS-12 (Forgotten Joint Score) Web Application
Author: Doç. Dr. Özgür Karakoyun project
Stack: Flask + SQLite, deployable on Railway
Procedures: knee, hip, osseointegration, socket_prosthesis
"""

import os
import json
import csv
import io
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, abort, Response, flash, g
)

from translations import LANGUAGES, QUESTIONS, ANSWERS, T, t, PROCEDURES, AMPUTEE_PROCEDURES
from scoring import calculate_fjs_score, score_label

# ---------- Configuration ----------
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'fjs.db'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-dev-only-secret-key-12345')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin1234')  # CHANGE in Railway env vars!

DEFAULT_LANG = 'tr'

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ---------- Database ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now')),
    language TEXT,
    name TEXT NOT NULL,
    age INTEGER,
    procedure_type TEXT NOT NULL,        -- 'knee' | 'hip' | 'osseointegration' | 'socket_prosthesis'
    side TEXT NOT NULL,                  -- 'right' | 'left' | 'bilateral'

    -- Surgery dates (knee/hip surgery, or osseointegration surgery)
    surgery_month_right INTEGER,
    surgery_year_right INTEGER,
    surgery_month_left INTEGER,
    surgery_year_left INTEGER,

    -- Amputation info (osseointegration: year+level; socket: month+year+level)
    amputation_month_right INTEGER,
    amputation_year_right INTEGER,
    amputation_level_right TEXT,
    amputation_month_left INTEGER,
    amputation_year_left INTEGER,
    amputation_level_left TEXT,

    -- Scores
    fjs_score_right REAL,
    fjs_score_left REAL,
    fjs_score_unilateral REAL,

    -- Raw answers (JSON list/lists of ints)
    answers_json TEXT
);
"""


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and run lightweight migrations for existing databases."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    # Add new columns if upgrading from an older schema
    cursor = conn.execute("PRAGMA table_info(responses)")
    columns = {row[1] for row in cursor.fetchall()}
    for new_col, sql_type in [
        ('amputation_month_right', 'INTEGER'),
        ('amputation_month_left', 'INTEGER'),
    ]:
        if new_col not in columns:
            conn.execute(f"ALTER TABLE responses ADD COLUMN {new_col} {sql_type}")
    conn.commit()
    conn.close()


# ---------- Helpers ----------
def get_lang():
    """Return current language code; default Turkish."""
    lang = (request.args.get('lang') or
            request.form.get('lang') or
            session.get('lang') or
            DEFAULT_LANG)
    if lang not in LANGUAGES:
        lang = DEFAULT_LANG
    session['lang'] = lang
    return lang


@app.context_processor
def inject_globals():
    lang = session.get('lang', DEFAULT_LANG)
    return {
        'lang': lang,
        'lang_dir': LANGUAGES[lang]['dir'],
        'languages': LANGUAGES,
        't': lambda key, **kw: t(lang, key, **kw),
        'T': T.get(lang, T[DEFAULT_LANG]),
    }


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper


def safe_json_loads(value):
    """Decode JSON safely; return an empty dict if old/broken data exists."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {}


def answer_text(lang, value):
    """Return localized answer text for a numeric FJS answer."""
    if value is None:
        return ''
    try:
        value = int(value)
    except (TypeError, ValueError):
        return ''
    options = ANSWERS.get(lang) or ANSWERS[DEFAULT_LANG]
    if 0 <= value < len(options):
        return options[value]
    return ''


def get_answer_lists(row):
    """Return right, left and unilateral answer lists from stored answers_json."""
    payload = safe_json_loads(row['answers_json'])
    side = row['side']

    right_answers = [''] * 12
    left_answers = [''] * 12
    unilateral_answers = [''] * 12

    if side == 'bilateral':
        right = payload.get('right') or []
        left = payload.get('left') or []
        for i in range(12):
            right_answers[i] = right[i] if i < len(right) else ''
            left_answers[i] = left[i] if i < len(left) else ''
    else:
        answers = payload.get('answers') or []
        for i in range(12):
            unilateral_answers[i] = answers[i] if i < len(answers) else ''
        if side == 'right':
            right_answers = unilateral_answers[:]
        elif side == 'left':
            left_answers = unilateral_answers[:]

    return right_answers, left_answers, unilateral_answers


# ---------- Routes ----------
@app.route('/')
def index():
    get_lang()
    return render_template('index.html')


@app.route('/start', methods=['GET', 'POST'])
def patient_info():
    lang = get_lang()
    if request.method == 'POST':
        form = request.form
        name = (form.get('name') or '').strip()
        age = form.get('age', type=int)
        procedure_type = form.get('procedure_type')
        side = form.get('side')

        errors = []
        if not name:
            errors.append('name')
        if not procedure_type or procedure_type not in PROCEDURES:
            errors.append('procedure_type')
        if not side or side not in ('right', 'left', 'bilateral'):
            errors.append('side')

        # Surgery dates (knee/hip/osseo only — NOT for socket prosthesis)
        sm_r = form.get('surgery_month_right', type=int)
        sy_r = form.get('surgery_year_right', type=int)
        sm_l = form.get('surgery_month_left', type=int)
        sy_l = form.get('surgery_year_left', type=int)

        # Amputation info (amputee procedures only)
        amp_m_r = form.get('amputation_month_right', type=int)
        amp_y_r = form.get('amputation_year_right', type=int)
        amp_l_r = form.get('amputation_level_right')
        amp_m_l = form.get('amputation_month_left', type=int)
        amp_y_l = form.get('amputation_year_left', type=int)
        amp_l_l = form.get('amputation_level_left')

        if procedure_type in ('knee', 'hip', 'osseointegration'):
            if side in ('right', 'bilateral') and not (sm_r and sy_r):
                errors.append('surgery_date_right')
            if side in ('left', 'bilateral') and not (sm_l and sy_l):
                errors.append('surgery_date_left')

        if procedure_type == 'osseointegration':
            # Year + level required (month not asked)
            if side in ('right', 'bilateral') and not (amp_y_r and amp_l_r):
                errors.append('amputation_right')
            if side in ('left', 'bilateral') and not (amp_y_l and amp_l_l):
                errors.append('amputation_left')

        if procedure_type == 'socket_prosthesis':
            # Month + year + level required (no surgery date)
            if side in ('right', 'bilateral') and not (amp_m_r and amp_y_r and amp_l_r):
                errors.append('amputation_right')
            if side in ('left', 'bilateral') and not (amp_m_l and amp_y_l and amp_l_l):
                errors.append('amputation_left')

        if errors:
            flash(t(lang, 'required_error'), 'error')
            return render_template('patient_info.html', form=form, errors=errors)

        # Clear fields that don't apply to the selected procedure
        is_amputee = procedure_type in AMPUTEE_PROCEDURES
        is_socket = procedure_type == 'socket_prosthesis'

        session['patient'] = {
            'language': lang,
            'name': name,
            'age': age,
            'procedure_type': procedure_type,
            'side': side,
            # Surgery dates: only for knee/hip/osseo
            'surgery_month_right': sm_r if not is_socket else None,
            'surgery_year_right': sy_r if not is_socket else None,
            'surgery_month_left': sm_l if not is_socket else None,
            'surgery_year_left': sy_l if not is_socket else None,
            # Amputation info: socket needs full date; osseo needs year only
            'amputation_month_right': amp_m_r if is_socket else None,
            'amputation_year_right': amp_y_r if is_amputee else None,
            'amputation_level_right': amp_l_r if is_amputee else None,
            'amputation_month_left': amp_m_l if is_socket else None,
            'amputation_year_left': amp_y_l if is_amputee else None,
            'amputation_level_left': amp_l_l if is_amputee else None,
        }
        return redirect(url_for('questions'))

    return render_template('patient_info.html', form={}, errors=[])


@app.route('/questions', methods=['GET', 'POST'])
def questions():
    lang = get_lang()
    patient = session.get('patient')
    if not patient:
        return redirect(url_for('patient_info'))

    questions_text = QUESTIONS[lang]
    answer_options = ANSWERS[lang]
    bilateral = patient['side'] == 'bilateral'

    if request.method == 'POST':
        if bilateral:
            answers_right, answers_left = [], []
            for i in range(12):
                answers_right.append(request.form.get(f'q{i}_right', type=int))
                answers_left.append(request.form.get(f'q{i}_left', type=int))
            score_right = calculate_fjs_score(answers_right)
            score_left = calculate_fjs_score(answers_left)
            score_unilateral = None
            answers_payload = {'right': answers_right, 'left': answers_left}
        else:
            ans = [request.form.get(f'q{i}', type=int) for i in range(12)]
            single_score = calculate_fjs_score(ans)
            if patient['side'] == 'right':
                score_right, score_left, score_unilateral = single_score, None, single_score
            else:
                score_right, score_left, score_unilateral = None, single_score, single_score
            answers_payload = {'side': patient['side'], 'answers': ans}

        db = get_db()
        cur = db.execute(
            """INSERT INTO responses
               (language, name, age, procedure_type, side,
                surgery_month_right, surgery_year_right,
                surgery_month_left, surgery_year_left,
                amputation_month_right, amputation_year_right, amputation_level_right,
                amputation_month_left,  amputation_year_left,  amputation_level_left,
                fjs_score_right, fjs_score_left, fjs_score_unilateral,
                answers_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                patient['language'], patient['name'], patient['age'],
                patient['procedure_type'], patient['side'],
                patient['surgery_month_right'], patient['surgery_year_right'],
                patient['surgery_month_left'], patient['surgery_year_left'],
                patient['amputation_month_right'], patient['amputation_year_right'], patient['amputation_level_right'],
                patient['amputation_month_left'],  patient['amputation_year_left'],  patient['amputation_level_left'],
                score_right, score_left, score_unilateral,
                json.dumps(answers_payload, ensure_ascii=False),
            )
        )
        db.commit()
        new_id = cur.lastrowid
        session.pop('patient', None)
        return redirect(url_for('result', response_id=new_id))

    return render_template(
        'questions.html',
        patient=patient,
        questions=questions_text,
        answers=answer_options,
        bilateral=bilateral,
    )


@app.route('/result/<int:response_id>')
def result(response_id):
    lang = get_lang()
    db = get_db()
    row = db.execute('SELECT * FROM responses WHERE id = ?', (response_id,)).fetchone()
    if not row:
        abort(404)
    return render_template(
        'results.html',
        r=row,
        score_label_right=score_label(row['fjs_score_right'], lang) if row['fjs_score_right'] is not None else '',
        score_label_left=score_label(row['fjs_score_left'], lang) if row['fjs_score_left'] is not None else '',
        score_label_uni=score_label(row['fjs_score_unilateral'], lang) if row['fjs_score_unilateral'] is not None else '',
    )


# ---------- Admin ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    get_lang()
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw and pw == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_responses'))
        flash('Wrong password', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_responses():
    db = get_db()
    rows = db.execute('SELECT * FROM responses ORDER BY created_at DESC').fetchall()
    return render_template('admin.html', rows=rows)


@app.route('/admin/export.csv')
@admin_required
def admin_export_csv():
    db = get_db()
    rows = db.execute('SELECT * FROM responses ORDER BY created_at DESC').fetchall()

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel UTF-8 compatibility
    writer = csv.writer(output)

    base_headers = [
        'id', 'created_at', 'language', 'name', 'age',
        'procedure_type', 'side',
        'surgery_month_right', 'surgery_year_right',
        'surgery_month_left',  'surgery_year_left',
        'amputation_month_right', 'amputation_year_right', 'amputation_level_right',
        'amputation_month_left',  'amputation_year_left',  'amputation_level_left',
        'fjs_right', 'fjs_left', 'fjs_unilateral',
    ]
    answer_headers = []
    for i in range(1, 13):
        answer_headers.extend([f'right_q{i}_value', f'right_q{i}_answer'])
    for i in range(1, 13):
        answer_headers.extend([f'left_q{i}_value', f'left_q{i}_answer'])
    for i in range(1, 13):
        answer_headers.extend([f'unilateral_q{i}_value', f'unilateral_q{i}_answer'])
    writer.writerow(base_headers + answer_headers + ['answers_json'])

    for r in rows:
        lang = r['language'] if r['language'] in ANSWERS else DEFAULT_LANG
        right_answers, left_answers, unilateral_answers = get_answer_lists(r)

        answer_values = []
        for value in right_answers:
            answer_values.extend([value, answer_text(lang, value)])
        for value in left_answers:
            answer_values.extend([value, answer_text(lang, value)])
        for value in unilateral_answers:
            answer_values.extend([value, answer_text(lang, value)])

        writer.writerow([
            r['id'], r['created_at'], r['language'], r['name'], r['age'],
            r['procedure_type'], r['side'],
            r['surgery_month_right'], r['surgery_year_right'],
            r['surgery_month_left'],  r['surgery_year_left'],
            r['amputation_month_right'], r['amputation_year_right'], r['amputation_level_right'],
            r['amputation_month_left'],  r['amputation_year_left'],  r['amputation_level_left'],
            r['fjs_score_right'], r['fjs_score_left'], r['fjs_score_unilateral'],
        ] + answer_values + [r['answers_json']])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename=fjs_responses_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        },
    )


# ---------- Health check ----------
@app.route('/healthz')
def healthz():
    return 'ok', 200


# ---------- Bootstrap ----------
with app.app_context():
    init_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
