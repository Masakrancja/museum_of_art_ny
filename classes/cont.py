import datetime
import sqlite3
import json
import re
import hashlib
from flask import abort
class Cont():
    def __init__(self, conn, museum_api):
        self.conn = conn
        self.museum_api = museum_api
        self.cols_to_update = self.get_cols_to_update(table="arts_content")
        self.cols_to_insert = self.get_cols_to_insert(table="arts_content")
        self.cols_to_content = self.get_cols_to_content(table="arts_content")


    def get_content(self, art_id):
        """
        Get content to given art id from museum api
        and check if all is OK
        :param art_id: integer
        :return: collection
        """
        object = self.museum_api.get_object(art_id)
        if (object.status_code == 200):
            return json.loads(object.text)
        else:
            abort(object.status_code, object.reason)

    def check_if_update_art_content_is_needed(self, art_id, department_id, seconds=3600):
        """
        Check if is needed update content of arts id in chosen department id
        :param art_id: integer
        :param department_id: integer
        :param seconds: integer
        :return: True, if param seconds is greats than different between time from
        last saved content to now, otherwise False
        """
        earlier = datetime.datetime.now() - datetime.timedelta(seconds=seconds)
        try:
            cursor = self.conn.cursor()
            sql = "SELECT updated_at FROM arts_content WHERE art_id = ? and department_id = ?"
            sql_data = (art_id, department_id)
            cursor.execute(sql, sql_data);
            result = cursor.fetchone()
            if result:
                if datetime.datetime.strptime(result['updated_at'], "%Y-%m-%d %H:%M:%S") > earlier:
                    return False
            return True
        except sqlite3.Error as err:
            abort(500, description=f"Error database - check_if_update_art_content {err}")


    def update_content(self, art_id, department_id):
        """
        Update content of particulary art do database
        :param art_id: Integer
        :param department_id: Integer
        :return: Boolean
        """
        now = datetime.datetime.now()
        format_string = "%Y-%m-%d %H:%M:%S"
        now_string = now.strftime(format_string)
        cursor = self.conn.cursor()
        r = self.get_content(art_id)
        data_to_update = []
        for col in self.cols_to_update:
            if col == 'department_id':
                data_to_update.append(department_id)
            elif col == 'updated_at':
                data_to_update.append(now_string)
            elif col == 'additionalImages':
                data_to_update.append(';'.join(r[col]))
            else:
                data_to_update.append(r[col])
        data_to_insert = [art_id] + data_to_update
        try:
            sql = "SELECT id FROM arts_content WHERE art_id = ?"
            sql_data = (art_id,)
            cursor.execute(sql, sql_data)
            result = cursor.fetchone()
            if result:
                sql = "UPDATE arts_content SET " + ', '.join([x + ' = ?' for x in self.cols_to_update]) + \
                      " WHERE art_id = ?"
                data_to_update = tuple(data_to_update + [art_id])
                cursor.execute(sql, data_to_update)
            else:
                sql = "INSERT INTO arts_content (" + ', '.join(self.cols_to_insert) + ") VALUES (" + ', '.join(
                    len(self.cols_to_insert) * '?') + ")"
                data_to_insert = tuple(data_to_insert)
                cursor.execute(sql, data_to_insert)
            self.conn.commit()
        except sqlite3.Error as err:
            abort(500, description=f"Error database - update_content {err}")


    def get_cols_names_from_table(self, table:str) -> list:
        """
        Get names of columns for given table i database
        :param table: string
        :return: list
        """
        result = []
        try:
            cursor = self.conn.cursor();
            sql = "SELECT name FROM pragma_table_info(?)"
            sql_data = (table,)
            cursor.execute(sql, sql_data)
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    result.append(row['name'])
            return result
        except sqlite3.Error as err:
            abort(500, description=f"Error database - update_content {err}")


    def del_cols_names_from_table(self, cols:list, cols_to_delete:list) -> list:
        """
        Delete given names in list 'cols_to_delete' from list names given in 'cols'
        :param cols: list
        :param cols_to_delete: list
        :return: list
        """
        for col_to_delete in cols_to_delete:
            if col_to_delete in cols:
                del cols[cols.index(col_to_delete)]
        return cols


    def get_cols_to_update(self, table="arts_content"):
        """
        Get list names of columns needs to update to chosen database
        :param table: string
        :return: list
        """
        cols_to_delete = ['id', 'art_id']
        cols = self.get_cols_names_from_table(table)
        return self.del_cols_names_from_table(cols, cols_to_delete)


    def get_cols_to_insert(self, table="arts_content"):
        """
        Get list names of columns needs to insert to chosen database
        :param table: string
        :return: list
        """
        cols_to_delete = ['id']
        cols = self.get_cols_names_from_table(table)
        return self.del_cols_names_from_table(cols, cols_to_delete)

    def get_cols_to_content(self, table="arts_content"):
        """
        Get list names of columns which have a content to create view
        :param table: string
        :return: list
        """
        cols_to_delete = ['id', 'primaryImage', 'additionalImages', 'metadataDate', 'updated_at']
        cols = self.get_cols_names_from_table(table)
        return self.del_cols_names_from_table(cols, cols_to_delete)


    def get_contents(self, arts_id):
        """
        Get contents from database by given list including numbers id of arts
        :param arts_id: list
        :return: list of dicts
        """
        result = []
        try:
            cursor = self.conn.cursor()
            for art_id in arts_id:
                sql = "SELECT " + ', '.join(self.cols_to_content) + " FROM arts_content WHERE art_id = ?"
                sql_data = (art_id,)
                cursor.execute(sql, sql_data)
                row = cursor.fetchone()
                if row:
                    tab = {}
                    row = dict(row)
                    tab['art_id'] = row.pop('art_id')
                    tab['title'] = row.pop('title')
                    tab['image'] = row.pop('primaryImageSmall')
                    if row['isHighlight'] == 1:
                        row['isHighlight'] = 'Yes'
                    else:
                        row['isHighlight'] = 'No'
                    tab['desc'] = row
                    result.append(tab)
            return result
        except sqlite3.Error as err:
            abort(500, description=f"Error database - get_contents {err}")


    def get_human_name(self, name):
        """
        Get pretty name from column name
        :param name: string
        :return: string
        """
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return name[0:1].upper() + name[1:] + ':'


    def get_cols_to_need_names(self, table="arts_content"):
        """
        Get list names of columns which have a content to create view and which needs pretty name
        :param table: string
        :return: list
        """
        cols_to_delete = ['id', 'art_id', 'primaryImage', 'primaryImageSmall', 'additionalImages', 'title',
                          'metadataDate', 'department_id', 'updated_at']
        cols = self.get_cols_names_from_table(table)
        return self.del_cols_names_from_table(cols, cols_to_delete)


    def get_contents_from_user(self, contents, user_id):
        """
        Get content only for logged user
        :param contents: list of dicts
        :param user_id: integer
        :return: list of dicts
        """
        if user_id:
            for index, content in enumerate(contents):
                hash = self.create_hash(user_id, content['art_id'])
                contents[index]['hash'] = hash
                info, note, is_favorites = self.get_info_note(hash)
                contents[index]['info'] = info
                contents[index]['note'] = note
                contents[index]['is_favorites'] = is_favorites
        return contents


    def create_hash(self, user_id, art_id):
        """
        Create hashed string using given parameters
        :param user_id: string
        :param art_id: integer
        :return: string
        """
        return hashlib.sha256((user_id + str(art_id)).encode()).hexdigest()


    def get_info_note(self, hash):
        """
        Get info and note logged user using his hash created by method: 'create_hash'
        :param hash: string
        :return: tuple
        """
        try:
            result = ('', '', 0)
            cursor = self.conn.cursor()
            sql = "SELECT id FROM user_arts WHERE hash = ?"
            sql_data = (hash, )
            cursor.execute(sql, sql_data)
            row = cursor.fetchone()
            if row:
                sql = "SELECT info, note FROM user_arts_content WHERE user_arts_id = ?"
                sql_data = (row['id'], )
                cursor.execute(sql, sql_data)
                row = cursor.fetchone()
                if row:
                    result = (row['info'], row['note'], 1)
            return result
        except sqlite3.Error as err:
            abort(500, description=f"Error database - get_info_note {err}")


    def is_link(self, text):
        """
        check if giver text is a link
        :param text:
        :return:
        """
        result = re.match(r'^https?://', str(text))
        if result and result.span():
            return True
        return False


    def get_only_user_content(self, contents, user_id, me):
        """
        Get all content for particular user i he is logged and add to giver content
        :param contents: list of dicts
        :param user_id: integer
        :param me: enumerated
        :return: list of dicts
        """
        result = []
        if me == 'only-me':
            if user_id:
                for content in contents:
                    if self.has_user_this_art_id(content['art_id'], user_id):
                        result.append(content)
            return result
        return contents


    def has_user_this_art_id(self, art_id, user_id):
        """
        Check if user add given art_id to favorites
        :param art_id: Integer
        :param user_id: String
        :return: Boolean
        """
        try:
            cursor = self.conn.cursor()
            sql = "SELECT id FROM user_arts WHERE user_id = ? and art_id = ?"
            sql_data = (user_id, art_id)
            cursor.execute(sql, sql_data)
            row = cursor.fetchone()
            if row:
                return True
            return False
        except sqlite3.Error as err:
            abort(500, description=f"Error database - has_user_this_art_id {err}")
