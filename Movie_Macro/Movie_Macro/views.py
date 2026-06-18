"""
Routes and views for the flask application.
"""

import sqlite3
import secrets
import time
from datetime import datetime

from flask import render_template, request, redirect, url_for, session
from Movie_Macro import app
import random
from zoneinfo import ZoneInfo

DB_NAME = 'movie_macro.db'
def now_kst():
    return datetime.now(ZoneInfo("Asia/Seoul"))
RATE_LIMITS = {}
FLOW_MIN_SECONDS = {
    'schedule': 1.0,
    'seats': 2.0,
    'payment': 3.0,
}

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_code TEXT UNIQUE NOT NULL,
            userid TEXT NOT NULL,
            movie_code TEXT NOT NULL,
            movie_title TEXT NOT NULL,
            reserve_date TEXT NOT NULL,
            reserve_time TEXT NOT NULL,
            people_count INTEGER NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reservation_seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_code TEXT NOT NULL,
            seat TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT,
            action TEXT,
            movie_code TEXT,
            movie_title TEXT,
            reserve_date TEXT,
            reserve_time TEXT,
            seats TEXT,
            ip_address TEXT,
            created_at TEXT,
            status TEXT DEFAULT '정상'
        )
    
''')

    try:
        cur.execute("ALTER TABLE action_logs ADD COLUMN status TEXT DEFAULT '정상'")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE action_logs ADD COLUMN userid TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

def save_action_log(action, movie_code=None, movie_title=None, reserve_date=None, reserve_time=None, seats=None, status='정상'):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO action_logs (
            userid, action, movie_code, movie_title,
            reserve_date, reserve_time, seats, ip_address, created_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            session.get('user'),
            action,
            movie_code,
            movie_title,
            reserve_date,
            reserve_time,
            seats,
            request.remote_addr,
            now_kst().strftime('%Y-%m-%d %H:%M:%S'),
            status
        )
    )

    conn.commit()
    conn.close()

def get_actor_key():
    return f"{session.get('user', 'guest')}:{request.remote_addr}"

def rate_limit_exceeded(action, max_count, seconds):
    now = time.time()
    key = (get_actor_key(), action)
    recent = [stamp for stamp in RATE_LIMITS.get(key, []) if now - stamp < seconds]
    recent.append(now)
    RATE_LIMITS[key] = recent
    return len(recent) > max_count

def issue_macro_token(flow):
    token = secrets.token_urlsafe(24)
    tokens = session.get('macro_tokens', {})
    tokens[token] = {'flow': flow, 'created_at': time.time()}
    session['macro_tokens'] = tokens
    return token

def validate_macro_token(flow, token):
    tokens = session.get('macro_tokens', {})
    data = tokens.pop(token, None)
    session['macro_tokens'] = tokens

    if not data or data.get('flow') != flow:
        return False, '보안 토큰이 만료되었습니다. 페이지를 새로고침한 뒤 다시 시도해주세요.'

    elapsed = time.time() - float(data.get('created_at', 0))
    if elapsed < FLOW_MIN_SECONDS.get(flow, 0):
        return False, '너무 빠른 제출이 감지되었습니다. 잠시 후 다시 시도해주세요.'

    return True, None

def has_honeypot_value():
    return bool(request.form.get('company_name', '').strip())

def issue_payment_challenge():
    left = random.randint(2, 9)
    right = random.randint(2, 9)
    session['payment_challenge_answer'] = str(left + right)
    return {'left': left, 'right': right}

def validate_payment_challenge():
    expected = session.pop('payment_challenge_answer', None)
    answer = request.form.get('security_answer', '').strip()
    return expected is not None and answer == expected

MOVIES = {
    'mandalorian': {'title': '만달로리안과 그로구', 'genre': 'SF', 'runtime': '120분', 'poster': 'images/00_mandalorian.png'},
    'toystory5': {'title': '토이 스토리 5', 'genre': '애니메이션', 'runtime': '110분', 'poster': 'images/01_toystory_5.png'},
    'colony': {'title': '군체', 'genre': 'SF', 'runtime': '115분', 'poster': 'images/02_colony.png'},
    'wildssing': {'title': '와일드 씽', 'genre': '어드벤처', 'runtime': '105분', 'poster': 'images/03_wild_ssing.png'},
    'jinja': {'title': '신사', 'genre': '드라마', 'runtime': '100분', 'poster': 'images/04_jinja.png'},
    'backrooms': {'title': '백룸', 'genre': '공포', 'runtime': '95분', 'poster': 'images/05_backrooms.png'},
    'beforesunrise': {'title': '비포 선라이즈', 'genre': '로맨스', 'runtime': '101분', 'poster': 'images/06_before_sunrise.png'},
    'sheepinthebox': {'title': '상자 속의 양', 'genre': '애니메이션', 'runtime': '98분', 'poster': 'images/07_sheep_in_the_box.png'},
    'singstreet': {'title': '싱 스트리트', 'genre': '음악', 'runtime': '106분', 'poster': 'images/08_sing_street.png'},
    'asiatour': {'title': '플레이브 아시아 투어', 'genre': '공연', 'runtime': '125분', 'poster': 'images/09_asia_tour.png'}
}
@app.route('/')
@app.route('/home')
def home():
    movies = []

    for code, info in MOVIES.items():
        movies.append({
            'code': code,
            'title': info['title'],
            'genre': info['genre'],
            'runtime': info['runtime'],
            'poster': info['poster']
        })

    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.now().year,
        movies=movies
    )
'''
@app.route('/reserve')
def reserve():
    return render_template(
        'reserve.html',
        title='예매 페이지',
        year=datetime.now().year
    )
    '''

@app.route('/reserve/<movie_code>', methods=['GET', 'POST'])
def reserve(movie_code):
    if 'user' not in session:
        return redirect(url_for('login', message='예매 서비스를 이용하려면 먼저 로그인하세요.'))

    movie = MOVIES.get(movie_code)

    if movie is None:
        return "존재하지 않는 영화입니다."

    save_action_log(
    action='상영 일정 페이지 진입',
    movie_code=movie_code,
    movie_title=movie['title']
)

    date_options = ['2026-06-19', 
                    '2026-06-20', 
                    '2026-06-21',
                    '2026-06-22',
                    '2026-06-23',
                    '2026-06-24',
                    '2026-06-25',
                    '2026-06-26']
    time_options = ['13:00', '16:00', '19:00']

    selected_date = request.form.get('date', date_options[0])
    selected_time = request.form.get('time', time_options[0])
    error = None

    if request.method == 'POST':
        token_ok, error = validate_macro_token('schedule', request.form.get('macro_token'))

        if has_honeypot_value():
            error = '자동화된 요청이 감지되었습니다.'
            save_action_log('숨김 필드 탐지', movie_code, movie['title'], status='차단')
        elif rate_limit_exceeded('schedule_submit', 6, 60):
            error = '짧은 시간에 너무 많은 요청이 감지되었습니다. 잠시 후 다시 시도해주세요.'
            save_action_log('일정 선택 반복 요청', movie_code, movie['title'], status='차단')
        elif token_ok:
            return redirect(url_for(
                'seat_select',
                movie_code=movie_code,
                date=selected_date,
                time=selected_time
            ))

    return render_template(
        'schedule.html',
        title='상영 일정 선택',
        year=datetime.now().year,
        movie=movie,
        movie_code=movie_code,
        date_options=date_options,
        time_options=time_options,
        selected_date=selected_date,
        selected_time=selected_time,
        macro_token=issue_macro_token('schedule'),
        error=error
    )


@app.route('/reserve/<movie_code>/seats', methods=['GET', 'POST'])
def seat_select(movie_code):
    if 'user' not in session:
        return redirect(url_for('login', message='예매 서비스를 이용하려면 먼저 로그인하세요.'))

    movie = MOVIES.get(movie_code)

    if movie is None:
        return "존재하지 않는 영화입니다."


    seat_rows = {
    'A': [f'A{i}' for i in range(1, 21)],
    'B': [f'B{i}' for i in range(1, 21)],
    'C': [f'C{i}' for i in range(1, 21)],
    'D': [f'D{i}' for i in range(1, 21)],
    'E': [f'E{i}' for i in range(1, 21)],
    'F': [f'F{i}' for i in range(1, 21)],
    'G': [f'G{i}' for i in range(1, 21)],
    'H': [f'H{i}' for i in range(1, 21)],
    'I': [f'I{i}' for i in range(1, 21)],
    'J': [f'J{i}' for i in range(1, 21)],
}

    selected_date = request.values.get('date')
    selected_time = request.values.get('time')
    selected_people = request.values.get('people', '1')
    selected_seats = request.values.get('selected_seats', '')

    save_action_log(
        action='좌석 선택 페이지 진입',
        movie_code=movie_code,
        movie_title=movie['title'],
        reserve_date=selected_date,
        reserve_time=selected_time
    )

    if not selected_date or not selected_time:
        return redirect(url_for('reserve', movie_code=movie_code))

    conn = get_db_connection()
    cur = conn.cursor()

    rows = cur.execute(
    '''
    SELECT rs.seat
    FROM reservation_seats rs
    JOIN reservations r
      ON rs.reservation_code = r.reservation_code
    WHERE r.movie_code = ? AND r.reserve_date = ? AND r.reserve_time = ?
    ''',
    (movie_code, selected_date, selected_time)
).fetchall()

    reserved_seats = [row['seat'] for row in rows]

    conn.close()

    error = None
    
    if request.method == 'POST':
        token_ok, error = validate_macro_token('seats', request.form.get('macro_token'))
        requested_seats = [seat.strip() for seat in selected_seats.split(',') if seat.strip()]
        valid_seats = {seat for seats in seat_rows.values() for seat in seats}

        if has_honeypot_value():
            error = '자동화된 요청이 감지되었습니다.'
            save_action_log('좌석 선택 숨김 필드 탐지', movie_code, movie['title'], selected_date, selected_time, status='차단')
        elif rate_limit_exceeded('seat_submit', 8, 60):
            error = '짧은 시간에 좌석 선택 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
            save_action_log('좌석 선택 반복 요청', movie_code, movie['title'], selected_date, selected_time, status='차단')
        elif not token_ok:
            save_action_log('좌석 선택 보안 토큰 실패', movie_code, movie['title'], selected_date, selected_time, status='차단')
        elif not selected_people.isdigit() or not 1 <= int(selected_people) <= 8:
            error = '관람 인원은 1명부터 8명까지 선택할 수 있습니다.'
        elif len(requested_seats) == 0:
            error = '좌석을 선택해주세요.'
            selected_seats = ''
        elif len(requested_seats) != int(selected_people):
            error = '선택한 인원 수와 좌석 수가 일치해야 합니다.'
        elif len(set(requested_seats)) != len(requested_seats):
            error = '중복된 좌석이 포함되어 있습니다.'
        elif any(seat not in valid_seats for seat in requested_seats):
            error = '존재하지 않는 좌석이 포함되어 있습니다.'
        elif any(seat in reserved_seats for seat in requested_seats):
            error = '이미 예약된 좌석이 포함되어 있습니다. 다시 선택해주세요.'
            selected_seats = ''
        else:
            return redirect(url_for(
                'payment',
                movie_code=movie_code,
                date=selected_date,
                time=selected_time,
                people=selected_people,
                seats=','.join(requested_seats)
            ))


    return render_template(
        'seats.html',
        title='좌석 선택',
        year=datetime.now().year,
        movie=movie,
        movie_code=movie_code,
        selected_date=selected_date,
        selected_time=selected_time,
        selected_people=selected_people,
        selected_seats=selected_seats,
        reserved_seats=reserved_seats,
        seat_rows=seat_rows,
        error=error,
        macro_token=issue_macro_token('seats')
    )

@app.route('/payment/<movie_code>', methods=['GET', 'POST'])
def payment(movie_code):
    if 'user' not in session:
        return redirect(url_for('login', message='결제를 진행하려면 먼저 로그인하세요.'))

    movie = MOVIES.get(movie_code)

    if movie is None:
        return "존재하지 않는 영화입니다."

    
    selected_date = request.values.get('date')
    selected_time = request.values.get('time')
    selected_people = request.values.get('people')
    selected_seats = request.values.get('seats')

    if not selected_date or not selected_time or not selected_people or not selected_seats:
        return redirect(url_for('reserve', movie_code=movie_code))

    seat_list = [seat.strip() for seat in selected_seats.split(',') if seat.strip()]
    valid_seats = {f'{row}{number}' for row in 'ABCDEFGHIJ' for number in range(1, 21)}

    if (
        not selected_people.isdigit()
        or not 1 <= int(selected_people) <= 8
        or len(seat_list) != int(selected_people)
        or len(set(seat_list)) != len(seat_list)
        or any(seat not in valid_seats for seat in seat_list)
    ):
        save_action_log('결제 URL 조작 의심', movie_code, movie['title'], selected_date, selected_time, selected_seats, '차단')
        return redirect(url_for('seat_select', movie_code=movie_code, date=selected_date, time=selected_time))

    total_price = int(selected_people) * 12000

    def render_payment(error=None):
        return render_template(
            'payment.html',
            title='결제 페이지',
            year=datetime.now().year,
            movie=movie,
            movie_code=movie_code,
            selected_date=selected_date,
            selected_time=selected_time,
            selected_people=selected_people,
            seat_list=seat_list,
            total_price=total_price,
            macro_token=issue_macro_token('payment'),
            payment_challenge=issue_payment_challenge(),
            error=error
        )

    if request.method == 'GET':
        save_action_log(
            action='결제 페이지 진입',
            movie_code=movie_code,
            movie_title=movie['title'],
            reserve_date=selected_date,
            reserve_time=selected_time,
            seats=', '.join(seat_list)
        )


    conn = get_db_connection()
    cur = conn.cursor()

    rows = cur.execute(
        '''
        SELECT rs.seat
        FROM reservation_seats rs
        JOIN reservations r
            ON rs.reservation_code = r.reservation_code
        WHERE r.movie_code = ? AND r.reserve_date = ? AND r.reserve_time = ?
        ''',
        (movie_code, selected_date, selected_time)
    ).fetchall()

    reserved_seats = [row['seat'] for row in rows]

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        token_ok, token_error = validate_macro_token('payment', request.form.get('macro_token'))

        if has_honeypot_value():
            conn.close()
            save_action_log('결제 숨김 필드 탐지', movie_code, movie['title'], selected_date, selected_time, ', '.join(seat_list), '차단')
            return render_payment('자동화된 요청이 감지되었습니다.')

        if rate_limit_exceeded('payment_submit', 5, 60):
            conn.close()
            save_action_log('결제 반복 요청', movie_code, movie['title'], selected_date, selected_time, ', '.join(seat_list), '차단')
            return render_payment('짧은 시간에 결제 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.')

        if not token_ok:
            conn.close()
            save_action_log('결제 보안 토큰 실패', movie_code, movie['title'], selected_date, selected_time, ', '.join(seat_list), '차단')
            return render_payment(token_error)

        if not validate_payment_challenge():
            conn.close()
            save_action_log('결제 보안 확인 실패', movie_code, movie['title'], selected_date, selected_time, ', '.join(seat_list), '차단')
            return render_payment('보안 확인 답이 올바르지 않습니다.')

        if not payment_method:
            conn.close()
            return render_payment('결제 수단을 선택해주세요.')
        

        if any(seat in reserved_seats for seat in seat_list):
            conn.close()
            save_action_log('이미 예약된 좌석 결제 시도', movie_code, movie['title'], selected_date, selected_time, ', '.join(seat_list), '차단')
            return redirect(url_for(
                'seat_select',
                movie_code=movie_code,
                date=selected_date,
                time=selected_time
            ))


        reservation_code = f"R{now_kst().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"

        cur.execute(
            '''
            INSERT INTO reservations (
                reservation_code, userid, movie_code, movie_title,
                reserve_date, reserve_time, people_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                reservation_code,
                session.get('user'),
                movie_code,
                movie['title'],
                selected_date,
                selected_time,
                int(selected_people)
            )
        )

        for seat in seat_list:
            cur.execute(
                '''
                INSERT INTO reservation_seats (reservation_code, seat)
                VALUES (?, ?)
                ''',
                (reservation_code, seat)
            )

        conn.commit()
        conn.close()

        save_action_log(
            action='예매 완료',
            movie_code=movie_code,
            movie_title=movie['title'],
            reserve_date=selected_date,
            reserve_time=selected_time,
            seats=', '.join(seat_list)
        )

        return render_template(
            'complete.html',
            title='예매 완료',
            year=datetime.now().year,
            movie=movie,
            selected_date=selected_date,
            selected_time=selected_time,
            selected_people=selected_people,
            selected_seats=', '.join(seat_list),
            reservation_code=reservation_code,
            user=session.get('user')
        )

    save_action_log(
        action='결제 정보 확인',
        movie_code=movie_code,
        movie_title=movie['title'],
        reserve_date=selected_date,
        reserve_time=selected_time,
        seats=', '.join(seat_list)
    )

    conn.close()

    return render_payment()

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = request.args.get('message')

    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        user = cur.execute(
            'SELECT * FROM users WHERE userid = ? AND password = ?',
            (userid, password)
        ).fetchone()

        conn.close()

        if user:
            session['user'] = userid
            return redirect(url_for('home'))
        else:
            return render_template(
                'login.html',
                title='로그인',
                year=now_kst().year,
                error='아이디 또는 비밀번호가 올바르지 않습니다.',
                message=message
            )

    return render_template(
        'login.html',
        title='로그인',
        year=now_kst().year,
        message=message
    )


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if password != password2:
            return render_template(
                'register.html',
                title='회원가입',
                year=now_kst().year,
                error='비밀번호가 일치하지 않습니다.'
            )

        conn = get_db_connection()
        cur = conn.cursor()

        existing_user = cur.execute(
            'SELECT * FROM users WHERE userid = ?',
            (userid,)
        ).fetchone()

        if existing_user:
            conn.close()
            return render_template(
                'register.html',
                title='회원가입',
                year=now_kst().year,
                error='이미 존재하는 아이디입니다.'
            )

        cur.execute(
            'INSERT INTO users (userid, password) VALUES (?, ?)',
            (userid, password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template(
        'register.html',
        title='회원가입',
        year=now_kst().year
    )

@app.route('/my_reservations')
def my_reservations():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    rows = cur.execute(
        '''
        SELECT
            r.id,
            r.reservation_code,
            r.movie_title,
            r.reserve_date,
            r.reserve_time,
            r.people_count,
            GROUP_CONCAT(rs.seat, ', ') AS seats
        FROM reservations r
        JOIN reservation_seats rs
          ON r.reservation_code = rs.reservation_code
        WHERE r.userid = ?
        GROUP BY r.id
        ORDER BY r.reserve_date, r.reserve_time
        ''',
        (session.get('user'),)
    ).fetchall()

    conn.close()

    return render_template(
        'my_reservations.html',
        reservations=rows
    )

@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    conn = get_db_connection()
    cur = conn.cursor()

    reservation = cur.execute(
        'SELECT * FROM reservations WHERE id = ?',
        (reservation_id,)
    ).fetchone()

    if reservation:
        code = reservation['reservation_code']

        cur.execute('DELETE FROM reservation_seats WHERE reservation_code = ?', (code,))
        cur.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('my_reservations'))

@app.route('/logs')
def logs():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    rows = cur.execute(
        '''
        SELECT *
        FROM action_logs
        ORDER BY created_at DESC
        LIMIT 100
        '''
    ).fetchall()

    conn.close()

    return render_template(
        'logs.html',
        title='행동 로그',
        year=now_kst().year,
        logs=rows
    )
