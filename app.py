from flask import Flask, render_template, request, session, redirect, jsonify
from flask_mysqldb import MySQL
from flask_session import Session
from uuid import uuid4
import hashlib
import json
from helpers.get_time import get_post_time
from helpers.dbfunc import check_user_exists

app = Flask(__name__)
app.secret_key = "OMG_SUPER_SECRET_PASSWORD"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "midterm"
app.config["MYSQL_CHARSET"] = "utf8mb4"
app.config["MYSQL_COLLATION"] = "utf8mb4_unicode_ci"

mysql = MySQL(app)


@app.route("/")
def index():
    is_login = False
    if session.get("token"):
        is_login = True

    user_id = None
    if is_login:
        # Get user_id if logged in
        user_id = session.get("user_id")
    else:
        # Assign random user_id if not logged in
        user_id = uuid4()

    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT 
                p.id, 
                u.username, 
                p.title, 
                p.content, 
                UNIX_TIMESTAMP(p.created_at) AS "created_at",  
                UNIX_TIMESTAMP(p.updated_at) AS "updated_at", 
                l.id AS like_id
            FROM posts p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id AND l.user_id = %s
            ORDER BY p.created_at DESC
        LIMIT 8;""",
        [user_id],
    )
    mysql.connection.commit()
    posts = cur.fetchall()

    # Get all notifications from recipient_id
    cur.execute(
        """
        SELECT 
            inbox.id, 
            users.username,
            inbox.content, 
            inbox.redirect_url, 
            inbox.type,
            UNIX_TIMESTAMP(inbox.created_at) AS "created_at"
        FROM inbox
        LEFT JOIN users ON inbox.sender_id = users.id
        WHERE inbox.recipient_id = %s
        ORDER BY inbox.created_at DESC LIMIT 6;
        """,
        [user_id],
    )
    mysql.connection.commit()
    notifications = cur.fetchall()
    cur.close()

    return render_template(
        "index.html",
        posts=posts,
        notifications=notifications,
        is_login=is_login,
        get_post_time=get_post_time,
    )


@app.route("/profile/<username>")
def profile(username):
    is_login = False
    if session.get("token"):
        is_login = True

    cur = mysql.connection.cursor()
    # Get user profile
    cur.execute(
        """SELECT id, username, bio, UNIX_TIMESTAMP(created_at) FROM users WHERE username=%s""",
        [username],
    )
    mysql.connection.commit()
    profile = cur.fetchall()

    # Get all notifications from recipient_id
    cur.execute(
        """
        SELECT 
            inbox.id, 
            users.username,
            inbox.content, 
            inbox.redirect_url, 
            inbox.type,
            UNIX_TIMESTAMP(inbox.created_at) AS "created_at"
        FROM inbox
        LEFT JOIN users ON inbox.sender_id = users.id
        WHERE inbox.recipient_id = %s
        ORDER BY inbox.created_at DESC LIMIT 6;
        """,
        [session.get("user_id")],
    )
    mysql.connection.commit()
    notifications = cur.fetchall()
    cur.close()

    if not profile:
        return render_template(
            "404.html",
            notifications=notifications,
            is_login=is_login,
            get_post_time=get_post_time,
        )

    return render_template(
        "profile.html",
        profile=profile,
        notifications=notifications,
        is_login=is_login,
        get_post_time=get_post_time,
    )


# === API ===


@app.route("/user", methods=["POST"])
def user():
    if request.method == "POST":
        username = json.loads(request.data)["username"]
        bio = json.loads(request.data)["bio"]
        cur = mysql.connection.cursor()

        # Check if username exists
        cur.execute("""SELECT * FROM users WHERE username=%s""", ([username],))
        mysql.connection.commit()
        user = cur.fetchone()

        if user and user[0] != session.get("user_id"):
            # Failed
            return jsonify({"status": "failed", "message": "Username already exists."})

        # Update username and bio
        cur.execute(
            """UPDATE users SET username=%s, bio=%s WHERE id=%s""",
            ([username], [bio], [session.get("user_id")]),
        )
        mysql.connection.commit()
        cur.close()

        # Success
        session["username"] = username
        return jsonify({"status": "success", "message": "Profile updated."})
    else:
        # Failed
        return jsonify({"status": "failed", "message": "You are not logged in."})


@app.route("/post/<post_id>", methods=["GET", "POST"])
def post(post_id):
    if request.method == "POST":
        is_login = False
        if session.get("token"):
            is_login = True

        user_id = None
        if is_login:
            # Get user_id if logged in
            user_id = session.get("user_id")
        else:
            # Assign random user_id if not logged in
            user_id = uuid4()

        cur = mysql.connection.cursor()
        cur.execute(
            """SELECT 
                p.id, 
                u.username, 
                p.title, 
                p.content, 
                UNIX_TIMESTAMP(p.created_at) AS "created_at",  
                UNIX_TIMESTAMP(p.updated_at) AS "updated_at", 
                l.id AS like_id
            FROM posts p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id AND l.user_id = %s
            WHERE p.id=%s;
            """,
            ([user_id], [post_id]),
        )
        mysql.connection.commit()
        post = cur.fetchone()
        cur.close()

        return jsonify(
            {
                "id": post[0],
                "username": post[1],
                "title": post[2],
                "content": post[3],
                "created_at": post[4],
                "updated_at": post[5],
                "likes_id": post[6],
            }
        )
    else:
        is_login = False
        if session.get("token"):
            is_login = True

        cur = mysql.connection.cursor()
        cur.execute(
            """SELECT 
                p.id, 
                u.username, 
                p.title, 
                p.content, 
                UNIX_TIMESTAMP(p.created_at) AS "created_at",  
                UNIX_TIMESTAMP(p.updated_at) AS "updated_at", 
                l.id AS like_id
            FROM posts p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id AND l.user_id = %s
            WHERE p.id=%s;
            """,
            ([session.get("user_id")], [post_id]),
        )
        mysql.connection.commit()
        post = cur.fetchone()

        # Get all notifications from recipient_id
        cur.execute(
            """
            SELECT 
                inbox.id, 
                users.username,
                inbox.content, 
                inbox.redirect_url, 
                inbox.type,
                UNIX_TIMESTAMP(inbox.created_at) AS "created_at"
            FROM inbox
            LEFT JOIN users ON inbox.sender_id = users.id
            WHERE inbox.recipient_id = %s
            ORDER BY inbox.created_at DESC LIMIT 6;
            """,
            [session.get("user_id")],
        )
        mysql.connection.commit()
        notifications = cur.fetchall()
        cur.close()

        if not post:
            return render_template(
                "404.html",
                notifications=notifications,
                is_login=is_login,
                get_post_time=get_post_time,
            )

        return render_template(
            "post.html",
            post=post,
            notifications=notifications,
            is_login=is_login,
            get_post_time=get_post_time,
        )


@app.route("/update/<post_id>", methods=["POST"])
def edit(post_id):
    if session.get("token"):
        user_id = session.get("user_id")
        title = json.loads(request.data)["title"]
        content = json.loads(request.data)["content"]
        cur = mysql.connection.cursor()
        cur.execute(
            """UPDATE posts SET title=%s, content=%s WHERE id=%s AND user_id=%s""",
            ([title], [content], [post_id], [user_id]),
        )
        mysql.connection.commit()
        cur.close()

        # Success
        return jsonify({"status": "success", "message": "Post updated."})
    else:
        # Failed
        return jsonify({"status": "failed", "message": "You are not logged in."})


@app.route("/delete/<post_id>")
def delete(post_id):
    if session.get("token"):
        cur = mysql.connection.cursor()
        cur.execute(
            """DELETE FROM posts WHERE id=%s AND user_id=%s""",
            ([post_id], [session.get("user_id")]),
        )
        mysql.connection.commit()
        cur.close()

        # Success
        return jsonify({"status": "success", "message": "Post deleted."})
    else:
        # Failed
        return jsonify({"status": "failed", "message": "You are not logged in."})


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        post_id = uuid4()
        user_id = session.get("user_id")
        title = json.loads(request.data)["title"]
        content = json.loads(request.data)["content"]
        cur = mysql.connection.cursor()
        cur.execute(
            """INSERT INTO posts (id, user_id, title, content) VALUES (%s, %s, %s, %s)""",
            ([post_id], [user_id], [title], [content]),
        )
        mysql.connection.commit()
        cur.close()

        # Success
        return jsonify({"status": "success", "message": "Post created."})
    else:
        is_login = False
        if session.get("token"):
            is_login = True

            cur = mysql.connection.cursor()
            # Get all notifications from recipient_id
            cur.execute(
                """
                SELECT 
                    inbox.id, 
                    users.username,
                    inbox.content, 
                    inbox.redirect_url, 
                    inbox.type,
                    UNIX_TIMESTAMP(inbox.created_at) AS "created_at"
                FROM inbox
                LEFT JOIN users ON inbox.sender_id = users.id
                WHERE inbox.recipient_id = %s
                ORDER BY inbox.created_at DESC LIMIT 6;
                """,
                [session.get("user_id")],
            )
            mysql.connection.commit()
            notifications = cur.fetchall()
            cur.close()
            return render_template(
                "create.html",
                is_login=is_login,
                notifications=notifications,
                get_post_time=get_post_time,
            )
        else:
            return redirect("/login")


@app.route("/star/<post_id>")
def star(post_id):
    if session.get("token"):
        id = uuid4()
        user_id = session.get("user_id")
        cur = mysql.connection.cursor()
        # Query to star or unstar if already starred
        cur.execute(
            """SELECT * FROM likes WHERE user_id=%s AND post_id=%s""",
            ([user_id], [post_id]),
        )
        mysql.connection.commit()
        star = cur.fetchone()
        if star:
            # Unstar
            cur.execute(
                """DELETE FROM likes WHERE user_id=%s AND post_id=%s""",
                ([user_id], [post_id]),
            )
            mysql.connection.commit()
            cur.close()

            # Success
            return jsonify({"status": "unstarred", "message": "Post unstarred."})
        else:
            # Star
            cur.execute(
                """INSERT INTO likes (id, user_id, post_id) VALUES (%s, %s, %s)""",
                ([id], [user_id], [post_id]),
            )
            mysql.connection.commit()

            # Send the notification to the inbox
            cur = mysql.connection.cursor()
            cur.execute(
                """
                INSERT INTO inbox (id, sender_id, recipient_id, content, redirect_url, type)
                SELECT %s, %s, posts.user_id, %s, %s, '1'
                FROM posts
                WHERE posts.id = %s;
                """,
                (
                    [uuid4()],
                    [user_id],
                    ["starred your post"],
                    ["/post/" + post_id],
                    [post_id],
                ),
            )
            mysql.connection.commit()
            cur.close()

            # Success
            return jsonify({"status": "starred", "message": "Post starred."})
    else:
        # Failed
        return jsonify({"status": "failed", "message": "You are not logged in."})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = json.loads(request.data)["username"]
        password = json.loads(request.data)["password"]
        password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        cur = mysql.connection.cursor()
        cur.execute(
            """SELECT * FROM users WHERE username=%s AND pwd=%s""",
            ([username], [password]),
        )
        mysql.connection.commit()
        user = cur.fetchone()
        cur.close()

        if user:
            # Success
            session["token"] = str(uuid4())
            session["user_id"] = user[0]
            session["username"] = user[1]
            return jsonify({"status": "success", "message": "Login success."})
        else:
            # Failed
            return jsonify({"status": "failed", "message": "Credentials are invalid."})
    else:
        is_login = False
        if session.get("token"):
            is_login = True
        return render_template("login.html", is_login=is_login)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = uuid4()
        username = json.loads(request.data)["username"]
        password = json.loads(request.data)["password"]
        password = hashlib.sha256(password.encode("utf-8")).hexdigest()

        # Check if user exists
        cur = mysql.connection.cursor()
        if check_user_exists(cur, username):
            return jsonify({"status": "failed", "message": "User already exists."})

        cur.execute(
            """INSERT INTO users (id, username, pwd) VALUES (%s, %s, %s)""",
            ([user_id], [username], [password]),
        )
        mysql.connection.commit()
        cur.close()

        # Success
        return jsonify({"status": "success", "message": "Registration successful."})
    else:
        is_login = False
        if session.get("token"):
            is_login = True
        return render_template("register.html", is_login=is_login)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(request.referrer)


if __name__ == "__main__":
    app.run(debug=True)
