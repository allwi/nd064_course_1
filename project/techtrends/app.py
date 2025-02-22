import sqlite3
import logging

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    try:
        connection = sqlite3.connect('database.db')
        connection.row_factory = sqlite3.Row
        app.config['DB_CONN_COUNTER'] += 1
        return connection
    except:
        app.logger.critical("Database connection cannot be opened. Does the file 'database.db' exist?")
        raise   # rethrow the exception

def get_num_posts():
    try:
        connection = get_db_connection()
        posts = connection.execute('SELECT * FROM posts').fetchall()
        connection.close()
        return len(posts)
    except:
        return -1   # return negative number to show that an error occurred and no posts are available

# Function to get a post using its ID
def get_post(post_id):
    try:
        connection = get_db_connection()
        post = connection.execute('SELECT * FROM posts WHERE id = ?',
                            (post_id,)).fetchone()
        connection.close()
        return post
    except:
        app.logger.error("Cannot retrieve post ID %s",post_id)
        return None

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'
app.config['DB_CONN_COUNTER'] = 0
app.config['APP_HEALTHY'] = True

# Define the main route of the web application 
@app.route('/')
def index():
    try:
        connection = get_db_connection()
        posts = connection.execute('SELECT * FROM posts').fetchall()
        connection.close()
        return render_template('index.html', posts=posts)
    except:
        app.logger.error('Cannot retrieve the posts from the DB')
        return render_template('server_error.html')

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.warning('Failed to retrieve post with ID %s',post_id)
        return render_template('404.html'), 404
    else:
        app.logger.debug("Retrieved post '%s' ID %s",post['title'], post_id)
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.debug("Retrieve 'About' page")
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            try:
                connection = get_db_connection()
                connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                             (title, content))
                connection.commit()
                connection.close()
                app.logger.info("Created article '%s'",title)
                return redirect(url_for('index'))
            except:
                app.logger.error("Creation of article '%s' failed", title)
                return render_template('server_error.html')
    return render_template('create.html')

@app.route('/healthz')
def status():
    if (app.config['APP_HEALTHY']):
        response = app.response_class(
                response=json.dumps({"result":"OK - healthy"}),
                status=200,
                mimetype='application/json'
        )
    else:
        response = app.response_class(
            response=json.dumps({"result": "Internal server error"}),
            status=500,
            mimetype='application/json'
        )
    return response

@app.route('/metrics')
def metrics():
    num_posts = get_num_posts()
    response = app.response_class(
            response=json.dumps({"db_connection_count": app.config['DB_CONN_COUNTER'], "post_count": num_posts}),
            status=200,
            mimetype='application/json'
    )
    return response

# start the application on port 3111
if __name__ == "__main__":
    # simple configuration. Better approach will be to read the config from file
    # so that it can be changed without touching the app itself.
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s:%(name)s - [%(asctime)s] %(funcName)s:%(message)s',
                        handlers=[
                            logging.FileHandler("log_file.log"),
                            logging.StreamHandler()
                        ]
                        )
    app.run(host='0.0.0.0', port='3111')
