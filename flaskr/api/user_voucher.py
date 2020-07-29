from flask import request, jsonify
from flask_restful import Resource
import sqlite3, os, random, string
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims
from flaskr import file_directory


def get_random_alphanumeric_string(length):
    letters_and_digits = string.ascii_letters + string.digits
    result_str = ''.join((random.choice(letters_and_digits) for i in range(length)))
    return result_str


class UserVoucher(Resource):
    @jwt_required
    def get(self, username):
        current_user = get_jwt_identity()
        if current_user != username:
            # need to log
            response = jsonify(data="You do not have authorized access to perform this action.")
            response.status_code = 401
            return response
        else:
            conn = sqlite3.connect(os.path.join(file_directory, "storage.db"))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM vouchers WHERE user_id = ?", (username,))
            conn.commit()
            vouchers = [dict(row) for row in c.fetchall()]
            conn.close()

            return jsonify(data=vouchers)

    @jwt_required
    def post(self, username):
        claims = get_jwt_claims()
        admin = claims['admin']

        if admin == 'y':
            conn = sqlite3.connect(os.path.join(file_directory, "storage.db"))
            c = conn.cursor()

            request_json_data = request.get_json(force=True)
            voucher_title = request_json_data["title"]
            # Validate if voucher code is in database
            while True:
                voucher_code = get_random_alphanumeric_string(8)
                c.execute(f"SELECT * FROM vouchers WHERE code='{voucher_code}'")
                if not c.fetchone():
                    break
            voucher_image = ""
            voucher_description = request_json_data["description"]
            voucher_amount = request_json_data["amount"]
            voucher_status = "unused"
            used_date = ""

            c.execute("INSERT INTO vouchers VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (voucher_title, voucher_code, voucher_description, voucher_image, voucher_amount, voucher_status,
                       used_date, username))
            conn.commit()
            conn.close()

            return jsonify(data="Voucher created with user id of {}".format(username))
        else:
            response = jsonify(data="You do not have authorized access to perform this action.")
            response.status_code = 401
            return response

    @jwt_required
    def put(self, username):
        identity = get_jwt_identity()
        if username != identity:
            # need to log
            response = jsonify(data="You do not have authorized access to perform this action.")
            response.status_code = 401
            return response
        else:
            import datetime
            request_json_data = request.get_json(force=True)
            code = request_json_data["code"]
            used_date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

            conn = sqlite3.connect(os.path.join(file_directory, "storage.db"))
            c = conn.cursor()
            c.execute("SELECT * FROM vouchers WHERE code = ? AND status = 'unused'", (code,))

            if c.fetchone():
                c.execute("UPDATE vouchers SET status = 'used', used_date = ? WHERE code = ?", (used_date, code,))
                conn.commit()
                conn.close()

                return jsonify(data=f"Voucher with the code {code} from username {username} has been used.")

            else:
                c.execute("SELECT * FROM vouchers WHERE code=? AND user_id=0", (code,))
                if c.fetchone():
                    conn.commit()
                    conn.close()
                    return jsonify(data="This is a general voucher")
                else:
                    conn.commit()
                    conn.close()

                    return jsonify(data=f"Voucher with the code {code} from username {username} has already been used.")
