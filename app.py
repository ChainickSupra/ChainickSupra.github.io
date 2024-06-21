from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)

app.secret_key = '123'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'rhy34ktr67'
app.config['MYSQL_DB'] = 'spraydb'

mysql = MySQL(app)

@app.route('/')
def index():
    query = request.args.get('query', '')
    page = int(request.args.get('page', 1))
    offset = (page - 1) * 15

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if query:
        cursor.execute('''SELECT accounts.id AS user_id, accounts.username, portfolios.id AS portfolio_id, portfolios.profession 
                          FROM accounts 
                          JOIN portfolios ON accounts.id = portfolios.user_id 
                          WHERE portfolios.profession LIKE %s 
                          LIMIT 15 OFFSET %s''', ('%' + query + '%', offset))
    else:
        cursor.execute('''SELECT accounts.id AS user_id, accounts.username, portfolios.id AS portfolio_id, portfolios.profession 
                          FROM accounts 
                          JOIN portfolios ON accounts.id = portfolios.user_id 
                          LIMIT 15 OFFSET %s''', (offset,))

    portfolios = cursor.fetchall()

    return render_template('index.html', portfolios=portfolios, page=page, query=query)

@app.route('/delete_portfolio/<int:portfolio_id>', methods=['POST'])
def delete_portfolio(portfolio_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT user_id FROM portfolios WHERE id = %s', [portfolio_id])
    portfolio = cursor.fetchone()

    if portfolio and portfolio['user_id'] == session['id']:
        cursor.execute('DELETE FROM portfolios WHERE id = %s', [portfolio_id])
        mysql.connection.commit()
        flash('Портфолио удалено', 'success')
    else:
        flash('Вы не можете удалить это портфолио', 'danger')

    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('profile', user_id=account['id']))
        else:
            msg = 'Неверные логин/пароль'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Аккаунт уже существует'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Неверный e-mail'
        elif not re.match(r'[A-Za-z0-9А-Яа-я]+', username):
            msg = 'Логин должен содержать только буквы или цифры'
        elif not username or not password or not email:
            msg = 'Пожалуйста, заполните поля'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = 'Вы успешно зарегистрировались'
    elif request.method == 'POST':
        msg = 'Пожалуйста, заполните поля'
    return render_template('register.html', msg=msg)

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM accounts WHERE id = %s', [user_id])
    user = cursor.fetchone()

    cursor.execute('SELECT * FROM profiles WHERE user_id = %s', [user_id])
    profile = cursor.fetchone()

    cursor.execute('SELECT * FROM gallery WHERE user_id = %s', [user_id])
    gallery = cursor.fetchall()

    cursor.execute('SELECT * FROM resumes WHERE user_id = %s', [user_id])
    resume = cursor.fetchone()

    if request.method == 'POST' and 'loggedin' in session and session['id'] == user_id:
        skills = request.form.get('skills')
        experience = request.form.get('experience')
        contact_info = request.form.get('contact_info')

        cursor.execute('REPLACE INTO profiles (user_id, skills, experience, contact_info) VALUES (%s, %s, %s, %s)',
                       (user_id, skills, experience, contact_info))
        mysql.connection.commit()
        return redirect(url_for('profile', user_id=user_id))

    return render_template('profile.html', user=user, profile=profile, gallery=gallery, resume=resume)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'loggedin' in session:
        user_id = session['id']
        image_url = request.form['image_url']
        description = request.form['description']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO gallery (user_id, image_url, description) VALUES (%s, %s, %s)', (user_id, image_url, description))
        mysql.connection.commit()
        
        return redirect(url_for('profile', user_id=user_id))
    return redirect(url_for('login'))

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'loggedin' in session:
        user_id = session['id']
        resume_text = request.form['resume_text']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('REPLACE INTO resumes (user_id, resume_text) VALUES (%s, %s)', (user_id, resume_text))
        mysql.connection.commit()
        
        return redirect(url_for('profile', user_id=user_id))
    return redirect(url_for('login'))

@app.route('/upload_portfolio', methods=['GET', 'POST'])
def upload_portfolio():
    if 'loggedin' in session:
        if request.method == 'POST':
            user_id = session['id']
            profession = request.form['profession']
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('REPLACE INTO portfolios (user_id, profession) VALUES (%s, %s)', (user_id, profession))
            mysql.connection.commit()
            
            return redirect(url_for('profile', user_id=user_id))
        return render_template('upload_portfolio.html')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=False)
