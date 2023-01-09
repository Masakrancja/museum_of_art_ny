import datetime
import sqlite3
import json
import hashlib
from flask import abort
class Arts():
    def __init__(self, conn, museum_api):
        self.conn = conn
        self.museum_api = museum_api


    def check_if_update_arts_is_needed(self, department_id, seconds=3600):
        earlier = datetime.datetime.now() - datetime.timedelta(seconds=seconds)
        try:
            cursor = self.conn.cursor()
            sql = "SELECT updated_at FROM arts WHERE department_id = ? LIMIT 1"
            sql_data = (department_id,)
            cursor.execute(sql, sql_data)
            result = cursor.fetchone()
            if result:
                if datetime.datetime.strptime(result['updated_at'], "%Y-%m-%d %H:%M:%S") > earlier:
                    return False
            return True
        except sqlite3.Error as err:
            abort(500, description=f"Error database - check_if_update_arts {err}")


    def get_arts(self, department_id):
        objects = self.museum_api.get_objects(department_id)
        if objects.status_code == 200:
            return json.loads(objects.text)
        else:
            abort(objects.status_code)


    def update_arts(self, arts_id, department_id):
        now = datetime.datetime.now()
        format_string = "%Y-%m-%d %H:%M:%S"
        now_string = now.strftime(format_string)
        try:
            cursor = self.conn.cursor()
            for art_id in arts_id['objectIDs']:
                sql = "SELECT id from arts WHERE art_id = ? and department_id = ?"
                sql_data = (art_id, department_id)
                cursor.execute(sql, sql_data)
                result = cursor.fetchone()
                if result:
                    sql = "UPDATE arts SET updated_at = ? WHERE id = ?"
                    sql_data = (now_string, result['id'])
                    cursor.execute(sql, sql_data)
                else:
                    sql = "INSERT INTO arts (art_id, department_id, updated_at) VALUES (?, ?, ?)"
                    #hash = hashlib.sha256(str(art_id).encode() + str(department_id).encode()).hexdigest()
                    sql_data = (art_id, department_id, now_string)
                    cursor.execute(sql, sql_data)
            self.conn.commit()
        except sqlite3.Error as err:
            abort(500, description=f"Error database - update_arts {err}")


    def get_arts_for_selected_page(self, page, department_id, max_for_page):
        result = []
        try:
            cursor = self.conn.cursor()
            sql = "SELECT art_id FROM arts WHERE department_id = ? ORDER BY art_id ASC LIMIT ?, ?"
            sql_data = (department_id, page * max_for_page, max_for_page)
            cursor.execute(sql, sql_data)
            rows = cursor.fetchall()
            for row in rows:
                result.append(row['art_id'])
            return result
        except sqlite3.Error as err:
            abort(500, description=f"Error database - get_objects_for_selected {err}")


    def get_user_arts_by_param(self, user_id, department_id, note, only_foto, has_my_info):
        result = []
        try:
            cursor = self.conn.cursor()
            sql = "SELECT ua.art_id FROM user_arts AS ua"
            sql += ' INNER JOIN user_arts_content AS uac ON ua.id = uac.user_arts_id'
            sql += ' INNER JOIN arts_content AS ac ON ua.art_id = ac.art_id'
            sql += ' WHERE ua.user_id = ?'
            sql_data = []
            sql_data.append(user_id)
            if department_id:
                sql += ' and department_id = ?'
                sql_data.append(department_id)
            if only_foto == 'yes':
                sql += ' and ac.primaryImage != ""'
            if has_my_info == 'yes':
                sql += ' and uac.info !=""'
            sql += ' ORDER BY uac.note ' + note
            cursor.execute(sql, tuple(sql_data))
            rows = cursor.fetchall()
            for row in rows:
                result.append(row['art_id'])
            return result
        except sqlite3.Error as err:
            abort(500, description=f"Error database - get_arts_by_param {err}")