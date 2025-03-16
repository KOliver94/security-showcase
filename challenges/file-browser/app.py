import os
import sqlite3
from functools import wraps

from flask import Flask, g, session, flash, redirect, url_for, request, render_template, abort, send_file
from werkzeug.security import check_password_hash

from generate_files import generate_files

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['DATABASE'] = 'file-browser.db'

BASE_DIR = os.path.join(os.getcwd(), "files")


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


@app.cli.command('generate-files')
def init_files_command():
    generate_files()


app.teardown_appcontext(close_db)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def is_safe_path(path):
    return path.startswith(BASE_DIR) or os.path.abspath(path).startswith(BASE_DIR)


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

        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('file_browser'))

        flash(error)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/')
@app.route('/files')
@login_required
def file_browser():
    requested_path = request.args.get('path', BASE_DIR)

    if not is_safe_path(requested_path):
        flash("Access denied: You can only browse within the application directory")
        return redirect(url_for('file_browser', path=BASE_DIR))

    try:
        file_list = os.listdir(requested_path)
        files = []

        for filename in file_list:
            full_path = os.path.join(requested_path, filename)
            is_dir = os.path.isdir(full_path)

            files.append({
                'name': filename,
                'is_dir': is_dir,
                'full_path': full_path
            })

        files.sort(key=lambda x: (not x['is_dir'], x['name']))

        return render_template('index.html', path=requested_path, files=files, base_dir=BASE_DIR)

    except Exception as e:
        flash(f"Error: {str(e)}")
        return render_template('index.html', path=requested_path, files=[], base_dir=BASE_DIR)


@app.route('/view')
@login_required
def view_file():
    file_path = request.args.get('file', '')

    if not file_path:
        abort(400, "No file specified")

    if not is_safe_path(file_path):
        flash("Access denied: You can only access files within the application directory")
        return redirect(url_for('file_browser', path=BASE_DIR))

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        return render_template('index.html',
                               path=os.path.dirname(file_path),
                               file_content=content,
                               current_file=os.path.basename(file_path),
                               base_dir=BASE_DIR)

    except Exception as e:
        flash(f"Error viewing file: {str(e)}")
        return redirect(url_for('file_browser', path=os.path.dirname(file_path) if file_path else BASE_DIR))


@app.route('/download')
@login_required
def download_file():
    file_path = request.args.get('file', '')

    if not file_path:
        abort(400, "No file specified")

    if not is_safe_path(file_path):
        flash("Access denied: You can only download files within the application directory")
        return redirect(url_for('file_browser', path=BASE_DIR))

    try:
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        flash(f"Error downloading file: {str(e)}")
        return redirect(url_for('file_browser', path=os.path.dirname(file_path) if file_path else BASE_DIR))


if __name__ == '__main__':
    app.run()
