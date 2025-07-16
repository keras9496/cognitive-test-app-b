import os
import json
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

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(instance_path, 'cognitive_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- 데이터베이스 모델 정의 ---
class DigitSpanResult(db.Model):
    __tablename__ = 'digit_span_results'
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='숫자 암기 테스트')
    high_score = db.Column(db.Integer, nullable=False) 
    failed_attempts = db.Column(db.Text, nullable=True) 

    def __repr__(self):
        return f'<DigitSpanResult {self.nickname} - Score: {self.high_score}>'

# --- 위스콘신 테스트 결과 모델 ---
class WisconsinResult(db.Model):
    __tablename__ = 'wisconsin_results'
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='위스콘신 카드 정렬 검사')
    # 위스콘신 테스트 결과 필드들
    perseverative_responses = db.Column(db.Integer, nullable=False)
    trials_to_complete_first_category = db.Column(db.Integer, nullable=False)
    failure_to_maintain_set = db.Column(db.Integer, nullable=False)
    correct_rate = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<WisconsinResult {self.nickname}>'

with app.app_context():
    db.create_all()

# --- 라우트(URL 경로) 정의 ---
@app.route("/")
def index():
    """사용자 정보 입력 페이지를 보여줍니다."""
    return render_template("index.html")

@app.route("/start", methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션에 저장하고 테스트 페이지로 이동시킵니다."""
    try:
        session.clear()
        session['nickname'] = request.form.get('nickname', '').strip()
        session['name'] = request.form.get('name', '').strip()
        session['age'] = int(request.form.get('age', 0))
        session['gender'] = request.form.get('gender', '').strip()
        session['test_date'] = request.form.get('test_date', '').strip()
        
        if not all([session['nickname'], session['name'], session['age'] > 0, session['gender'], session['test_date']]):
            return redirect(url_for('index'))
        
        session.modified = True
        return redirect(url_for('digit_span_test'))
        
    except (ValueError, TypeError) as e:
        print(f"사용자 입력 처리 중 오류: {e}")
        return redirect(url_for('index'))

@app.route("/test")
def digit_span_test():
    """숫자 암기 테스트 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('digit_span_test.html')

@app.route("/wisconsin-test")
def wisconsin_test():
    """위스콘신 카드 정렬 테스트 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('wisconsin_test.html')

# --- API 엔드포인트 ---
@app.route('/api/submit-result', methods=['POST'])
def submit_result():
    """숫자 암기 테스트 결과를 받아 데이터베이스에 저장합니다."""
    try:
        if 'nickname' not in session:
            return jsonify({"status": "error", "message": "세션이 만료되었습니다."}), 403

        data = request.get_json()
        if not data or 'highScore' not in data or 'failedAttempts' not in data:
            return jsonify({"status": "error", "message": "필수 데이터가 누락되었습니다."}), 400

        result_entry = DigitSpanResult(
            nickname=session.get('nickname'),
            name=session.get('name'),
            age=session.get('age'),
            gender=session.get('gender'),
            test_date=session.get('test_date'),
            high_score=int(data.get('highScore')),
            failed_attempts=json.dumps(data.get('failedAttempts', []))
        )
        
        db.session.add(result_entry)
        db.session.commit()
        
        print(f"{session.get('nickname')}님의 숫자 암기 테스트 결과가 DB에 저장되었습니다.")
        
        return jsonify({"status": "success", "message": "결과가 성공적으로 저장되었습니다."})

    except (ValueError, TypeError) as e:
        print(f"데이터 타입 변환 오류: {e}")
        return jsonify({"status": "error", "message": "잘못된 데이터 형식입니다."}), 400
    except Exception as e:
        db.session.rollback()
        print(f"결과 저장 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "결과 저장 중 서버 오류가 발생했습니다."}), 500

@app.route('/api/submit-wisconsin-result', methods=['POST'])
def submit_wisconsin_result():
    """위스콘신 테스트 결과를 받아 데이터베이스에 저장합니다."""
    try:
        if 'nickname' not in session:
            return jsonify({"status": "error", "message": "세션이 만료되었습니다."}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "필수 데이터가 누락되었습니다."}), 400

        result_entry = WisconsinResult(
            nickname=session.get('nickname'),
            name=session.get('name'),
            age=session.get('age'),
            gender=session.get('gender'),
            test_date=session.get('test_date'),
            perseverative_responses=data.get('perseverativeResponses'),
            trials_to_complete_first_category=data.get('trialsToCompleteFirstCategory'),
            failure_to_maintain_set=data.get('failureToMaintainSet'),
            correct_rate=data.get('correctRate')
        )
        
        db.session.add(result_entry)
        db.session.commit()
        
        print(f"{session.get('nickname')}님의 위스콘신 테스트 결과가 DB에 저장되었습니다.")
        
        return jsonify({"status": "success", "message": "결과가 성공적으로 저장되었습니다."})

    except Exception as e:
        db.session.rollback()
        print(f"위스콘신 결과 저장 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "결과 저장 중 서버 오류가 발생했습니다."}), 500

# --- 결과 페이지 (관리자용) ---
@app.route("/results")
def show_results():
    """모든 테스트 결과를 관리자에게 보여주는 페이지입니다."""
    password = request.args.get('pw')
    admin_pw = os.environ.get('ADMIN_PASSWORD', 'local_admin_pw')
    
    if password != admin_pw:
        return "접근 권한이 없습니다. 관리자 암호를 확인하세요.", 403

    try:
        results_raw = DigitSpanResult.query.order_by(DigitSpanResult.id.desc()).all()
        
        results = []
        for r in results_raw:
            if r.failed_attempts:
                try:
                    r.failed_attempts_list = json.loads(r.failed_attempts)
                except json.JSONDecodeError:
                    r.failed_attempts_list = []
            else:
                r.failed_attempts_list = []
            results.append(r)
            
        return render_template('results.html', results=results)
    except Exception as e:
        print(f"결과 페이지 렌더링 중 오류: {e}")
        return "결과를 불러오는 중 오류가 발생했습니다.", 500

@app.route("/wisconsin-results")
def show_wisconsin_results():
    """위스콘신 테스트 결과를 관리자에게 보여주는 페이지입니다."""
    password = request.args.get('pw')
    admin_pw = os.environ.get('ADMIN_PASSWORD', 'local_admin_pw')
    
    if password != admin_pw:
        return "접근 권한이 없습니다. 관리자 암호를 확인하세요.", 403
        
    try:
        results = WisconsinResult.query.order_by(WisconsinResult.id.desc()).all()
        return render_template('wisconsin_results.html', results=results)
    except Exception as e:
        print(f"위스콘신 결과 페이지 렌더링 중 오류: {e}")
        return "결과를 불러오는 중 오류가 발생했습니다.", 500

# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    app.run(debug=True, port=5001)