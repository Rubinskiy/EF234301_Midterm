def check_user_exists(cursor, username):
    cursor.execute("""SELECT * FROM users WHERE username = %s""", ([username]))
    if cursor.fetchone() is None:
        return False
    else:
        return True
