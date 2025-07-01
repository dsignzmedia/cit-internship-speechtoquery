def run_query(sql_query):
    import mysql.connector

    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'intern',
        'port': 3306
    }

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        return [list(row) for row in results]

    except mysql.connector.Error as err:
        return f"❌ Error: {err}"

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()