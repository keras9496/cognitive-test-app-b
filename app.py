import os
import json
import random
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# --- Flask 앱 초기 설정 ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development')

# --- 데이터베이스 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or \
    'sqlite:///' + os.path.join(instance_path, 'cognitive_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- 상수 정의 ---
SEQUENCE_LEVELS = [
    {'name': 'Level 1', 'box_count': 5, 'flash_count': 3},
    {'name': 'Level 2', 'box_count': 7, 'flash_count': 4},
    {'name': 'Level 3', 'box_count': 7, 'flash_count': 5},
]
PROBLEMS_PER_SEQUENCE_LEVEL = 5
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500
BOX_SIZE = 50

# --- 데이터베이스 모델 정의 ---

class ASetSequenceMemoryResult(db.Model):
    __tablename__ = 'a_set_sequence_memory_results'
    id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(80), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='A Set 시각 순서 기억 검사')
    level = db.Column(db.String(50), nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    avg_similarity = db.Column(db.Float, nullable=False)

class BSetDigitSpanResult(db.Model):
    __tablename__ = 'b_set_digit_span_results'
    id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(80), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='B Set 숫자 암기 테스트')
    high_score = db.Column(db.Integer, nullable=False)
    failed_attempts = db.Column(db.Text, nullable=True)

class WisconsinResult(db.Model):
    __tablename__ = 'wisconsin_results'
    id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(80), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='위스콘신 카드 정렬 검사')
    perseverative_responses = db.Column(db.Integer, nullable=False)
    trials_to_complete_first_category = db.Column(db.Integer, nullable=False)
    failure_to_maintain_set = db.Column(db.Integer, nullable=False)
    correct_rate = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# --- 핵심 로직 함수들 ---

def create_sequence_problem(level_index, is_practice=False):
    if is_practice:
        level_info = {'name': 'Practice', 'box_count': 3, 'flash_count': 2}
    elif level_index >= len(SEQUENCE_LEVELS):
        return None
    else:
        level_info = SEQUENCE_LEVELS[level_index]

    box_count = level_info['box_count']
    flash_count = level_info['flash_count']
    boxes = []
    max_x = CANVAS_WIDTH - BOX_SIZE
    max_y = CANVAS_HEIGHT - BOX_SIZE
    while len(boxes) < box_count:
        x1 = random.randint(0, max_x)
        y1 = random.randint(0, max_y)
        x2, y2 = x1 + BOX_SIZE, y1 + BOX_SIZE
        is_overlapping = any(not (x2 < b['x1'] or x1 > b['x2'] or y2 < b['y1'] or y1 > b['y2']) for b in boxes)
        if not is_overlapping:
            boxes.append({'id': len(boxes), 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
    
    flash_sequence = random.sample(range(box_count), flash_count)
    return {
        "level_name": level_info['name'], "flash_count": flash_count,
        "boxes": boxes, "flash_sequence": flash_sequence
    }

def save_a_set_sequence_results_to_db():
    try:
        if 'teacher_name' not in session or 'a_set_score' not in session:
            return False
        
        for level_name, data in session.get('a_set_score', {}).items():
            if not data.get('similarities'): continue
            avg_sim = sum(data['similarities']) / len(data['similarities'])
            result_entry = ASetSequenceMemoryResult(
                teacher_name=session['teacher_name'], user_name=session['user_name'], age=session['age'], gender=session['gender'],
                test_date=session['test_date'], level=level_name, correct=data['correct'],
                wrong=data['wrong'], avg_similarity=round(avg_sim, 4)
            )
            db.session.add(result_entry)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False

# --- 라우트(URL 경로) 정의 ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=['POST'])
def start_test():
    try:
        session.clear()
        session['teacher_name'] = request.form.get('teacher_name', '').strip()
        session['user_name'] = request.form.get('user_name', '').strip()
        session['age'] = int(request.form.get('age', 0))
        session['gender'] = request.form.get('gender', '').strip()
        session['test_date'] = request.form.get('test_date', '').strip()

        if not all([session['teacher_name'], session['user_name'], session['age'] > 0, session['gender'], session['test_date']]):
            return redirect(url_for('index'))

        a_set_count = ASetSequenceMemoryResult.query.filter_by(teacher_name=session['teacher_name'], user_name=session['user_name']).count()
        b_set_count = BSetDigitSpanResult.query.filter_by(teacher_name=session['teacher_name'], user_name=session['user_name']).count()
        total_tests = a_set_count + b_set_count
        
        session.modified = True

        if total_tests % 2 == 0:
            session['a_set_level_index'] = 0
            session['a_set_problem_in_level'] = 1
            session['a_set_score'] = {lvl['name']: {'correct': 0, 'wrong': 0, 'similarities': []} for lvl in SEQUENCE_LEVELS}
            return redirect(url_for('a_set_practice_page'))
        else:
            return redirect(url_for('b_set_digit_span_test'))
            
    except (ValueError, TypeError):
        return redirect(url_for('index'))

@app.route("/a-set/practice")
def a_set_practice_page():
    if 'teacher_name' not in session: return redirect(url_for('index'))
    return render_template('a_set_sequence_practice.html')

@app.route("/a-set/test")
def a_set_test_page():
    if 'teacher_name' not in session: return redirect(url_for('index'))
    return render_template('a_set_sequence_test.html')

@app.route("/b-set/test")
def b_set_digit_span_test():
    if 'teacher_name' not in session: return redirect(url_for('index'))
    return render_template('b_set_digit_span_test.html')

@app.route("/wisconsin-test")
def wisconsin_test():
    if 'teacher_name' not in session: return redirect(url_for('index'))
    return render_template('wisconsin_test.html')

# --- API 엔드포인트 ---

@app.route('/api/a-set/get-practice-problem')
def get_a_set_practice_problem():
    if 'teacher_name' not in session: return jsonify({"error": "Session not started"}), 403
    problem = create_sequence_problem(0, is_practice=True)
    session['a_set_practice_problem'] = problem
    session.modified = True
    return jsonify(problem)

@app.route('/api/a-set/submit-practice-answer', methods=['POST'])
def submit_a_set_practice_answer():
    data = request.get_json()
    user_answer = data.get('answer')
    correct_answer = session.get('a_set_practice_problem', {}).get('flash_sequence')
    return jsonify({"status": "correct" if user_answer == correct_answer else "incorrect"})

@app.route('/api/a-set/get-problem')
def get_a_set_problem():
    if 'teacher_name' not in session: return jsonify({"error": "Session not started"}), 403
    level_index = session.get('a_set_level_index', 0)
    if level_index >= len(SEQUENCE_LEVELS):
        if save_a_set_sequence_results_to_db():
            session.pop('a_set_score', None)
            session.modified = True
            return jsonify({"status": "completed", "next_url": url_for('wisconsin_test')})
        else:
            return jsonify({"error": "Failed to save results"}), 500

    problem = create_sequence_problem(level_index)
    session['a_set_current_problem'] = problem
    session.modified = True
    problem['problem_in_level'] = session.get('a_set_problem_in_level')
    problem['total_problems'] = PROBLEMS_PER_SEQUENCE_LEVEL
    return jsonify(problem)

@app.route('/api/a-set/submit-answer', methods=['POST'])
def submit_a_set_answer():
    data = request.get_json()
    user_answer = data.get('answer')
    problem = session.get('a_set_current_problem')
    correct_answer = problem['flash_sequence']
    
    matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
    similarity = matches / len(correct_answer) if correct_answer else 0
    level_name = problem['level_name']

    score_data = session['a_set_score'][level_name]
    score_data['correct'] += 1 if user_answer == correct_answer else 0
    score_data['wrong'] += 1 if user_answer != correct_answer else 0
    score_data['similarities'].append(similarity)
    
    session['a_set_problem_in_level'] += 1
    if session['a_set_problem_in_level'] > PROBLEMS_PER_SEQUENCE_LEVEL:
        session['a_set_level_index'] += 1
        session['a_set_problem_in_level'] = 1
        
    session.modified = True
    return jsonify({"status": "next_problem"})

@app.route('/api/submit-b-set-result', methods=['POST'])
def submit_b_set_result():
    if 'teacher_name' not in session: return jsonify({"status": "error"}), 403
    data = request.get_json()
    result_entry = BSetDigitSpanResult(
        teacher_name=session['teacher_name'], user_name=session['user_name'], age=session['age'],
        gender=session['gender'], test_date=session['test_date'],
        high_score=int(data.get('highScore', 0)),
        failed_attempts=json.dumps(data.get('failedAttempts', []))
    )
    db.session.add(result_entry)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/submit-wisconsin-result', methods=['POST'])
def submit_wisconsin_result():
    if 'teacher_name' not in session:
        return jsonify({"status": "error", "message": "세션 만료"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "데이터 없음"}), 400

    try:
        result_entry = WisconsinResult(
            teacher_name=session.get('teacher_name'),
            user_name=session.get('user_name'),
            age=session.get('age'),
            gender=session.get('gender'),
            test_date=session.get('test_date'),
            perseverative_responses=int(data.get('perseverativeResponses', 0)),
            trials_to_complete_first_category=int(data.get('trialsToCompleteFirstCategory', 0)),
            failure_to_maintain_set=int(data.get('failureToMaintainSet', 0)),
            correct_rate=float(data.get('correctRate', 0.0))
        )
        db.session.add(result_entry)
        db.session.commit()
        return jsonify({"status": "success", "message": "결과 저장 성공"})
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"데이터 형식 오류: {e}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"서버 오류: {e}"}), 500


# --- 결과 페이지 (관리자용) ---
@app.route("/results")
def show_results():
    password = request.args.get('pw')
    admin_pw = os.environ.get('ADMIN_PASSWORD', 'w123456789')
    if password != admin_pw: return "접근 권한이 없습니다.", 403

    try:
        a_set_seq_results = ASetSequenceMemoryResult.query.order_by(ASetSequenceMemoryResult.id.desc()).all()
        b_set_digit_results_raw = BSetDigitSpanResult.query.order_by(BSetDigitSpanResult.id.desc()).all()
        wisconsin_results = WisconsinResult.query.order_by(WisconsinResult.id.desc()).all()
        
        b_set_digit_results = []
        for r in b_set_digit_results_raw:
            try:
                r.failed_attempts_list = json.loads(r.failed_attempts or '[]')
            except json.JSONDecodeError:
                r.failed_attempts_list = []
            b_set_digit_results.append(r)

        return render_template(
            'results.html', 
            a_set_seq_results=a_set_seq_results,
            b_set_digit_results=b_set_digit_results,
            wisconsin_results=wisconsin_results
        )
    except Exception as e:
        return f"결과 페이지 로딩 중 오류 발생: {e}", 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)