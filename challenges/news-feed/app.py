import hashlib
import os
import sqlite3
from functools import wraps

from flask import Flask, render_template, g, session, flash, redirect, url_for, request

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['DATABASE'] = 'news-feed.db'
app.config['SESSION_COOKIE_HTTPONLY'] = False  # TODO: Remove this workaround


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.cli.command('init-db')
def init_db_command():
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    print('Initialized the database.')


app.teardown_appcontext(close_db)


def md5_hash(password):
    return hashlib.md5(password.encode()).hexdigest()


# Prevent XSS vulnerabilities
def sanitize_body(content):
    sanitized = content.replace("<script>", "")
    sanitized = sanitized.replace("</script>", "")
    return sanitized


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('Insufficient permissions', 'danger')
            return redirect(request.referrer or url_for('news'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."

        if error is None:
            hashed_password = md5_hash(password)

            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed_password)
            )
            db.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))

        flash(error)

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'Incorrect username.'

        elif not user['password'] == md5_hash(password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('news'))

        flash(error)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/')
@app.route('/news')
@login_required
def news():
    db = get_db()

    posts = db.execute(
        "SELECT p.id, title, body, created, user_id, username FROM posts p JOIN users u ON p.user_id = u.id").fetchall()

    posts = [dict(row) for row in posts]
    for post in posts:
        post['body'] = sanitize_body(post['body'])

    return render_template('index.html', posts=posts)


@app.route('/news/create', methods=['GET', 'POST'])
@login_required
def create_news():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'
        elif not body:
            error = 'Content is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()

            db.execute(
                'INSERT INTO posts (title, body, user_id) VALUES (?, ?, ?)',
                (title, body, session.get('user_id'))
            )
            db.commit()

            flash('Your post has been published!')
            return redirect(url_for('news'))

    return render_template('news_create.html')


@app.route('/news/edit/<news_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(news_id):
    db = get_db()

    query = f"""
        SELECT p.id, title, body, created, user_id, username
        FROM posts p JOIN users u ON p.user_id = u.id
        WHERE p.id = {news_id}
    """

    post = db.execute(query).fetchone()

    if post is None:
        flash('News post not found!')
        return redirect(url_for('news'))

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'
        elif not body:
            error = 'Content is required.'

        if error is not None:
            flash(error)
        else:
            db.execute(
                'UPDATE posts SET title = ?, body = ? WHERE id = ?',
                (title, body, post['id'])
            )
            db.commit()

            flash('Your post has been updated!')
            return redirect(url_for('news'))

    return render_template('news_create.html', post=post)


@app.route('/news/delete/<news_id>')
@login_required
@admin_required
def delete_news(news_id):
    db = get_db()

    query = f"DELETE FROM posts WHERE id = {news_id}"
    db.execute(query)
    db.commit()

    flash('Post deleted successfully!')

    return redirect(url_for('news'))


if __name__ == '__main__':
    app.run()
