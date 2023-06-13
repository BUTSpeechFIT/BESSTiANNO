import json
import pathlib
import random
import shutil
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

import db
from importlib.resources import path
from flask_httpauth import HTTPBasicAuth



import numpy as np
from flask import Flask, send_from_directory, jsonify, send_file, request, redirect, g

DATA_PREFIX = "/data"
EXPORT_DIR = "/data/export"
DATABASE = '/data/database.db'

app = Flask(__name__,
            static_folder='frontend/static')
auth = HTTPBasicAuth()

users = {
    "jean": {"password": generate_password_hash("1234X"), "roles": ["annotator"]},
    "katka": {"password": generate_password_hash("Z1234"), "roles": ["annotator"]},
    "viewer": {"password": generate_password_hash("1234AC"), "roles": ["viewer"]},
}


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            db.commit()
        data = np.loadtxt(f"{DATA_PREFIX}/lists/participants/valid_participants.scp", dtype=object)
        path_to_full_metadata = pathlib.Path(f"{DATA_PREFIX}/processed.list.csv")
        metadata = np.atleast_2d(np.loadtxt(path_to_full_metadata, dtype=object, delimiter=';'))
        meta = {int(pid): [cpl, cmt] for pid, cpl, cmt in metadata}

        sqlite_insert_participant = """INSERT INTO participant (id, complete, comment, gender) 
                                  VALUES (?, ?, ?, "M");"""

        sqlite_insert_segment = """INSERT INTO segments (start_time, end_time, label_id, participant_id) 
                                          VALUES (?, ?, (select id from segment_labels where name = ?), ?);"""

        for participant_id in data[:, 0].tolist():
            participant_id = int(participant_id)
            if participant_id in meta:
                completed = int(meta[participant_id][0])
                comment = meta[participant_id][1]
            else:
                completed = 0
                comment = ""

            if comment == "-":
                comment = ""
            db.cursor().execute(sqlite_insert_participant, [participant_id, completed, comment])
            path_to_full_segmentation = pathlib.Path(f"{DATA_PREFIX}/{participant_id}/segmentation.seg")
            if path_to_full_segmentation.exists():
                for st, et, label in np.loadtxt(path_to_full_segmentation, dtype=object, delimiter=";"):
                    db.cursor().execute(sqlite_insert_segment, [st, et, label, participant_id])
        db.commit()


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username)["password"], password):
        return users[username]


@auth.get_user_roles
def get_user_roles(user):
    return user["roles"]


def get_db():
    db_instance = getattr(g, '_database', None)
    if db_instance is None:
        db_instance = g._database = db.connect(DATABASE)
    return db_instance


@app.teardown_appcontext
def close_connection(exception):
    db_instance = getattr(g, '_database', None)
    if db_instance is not None:
        db_instance.close()


@app.route('/')
@auth.login_required
def index():
    print(auth.current_user())
    return send_from_directory('frontend', 'index.html')


@app.route('/detail/<int:participant_id>')
@auth.login_required
def detail(participant_id):
    return send_from_directory('frontend', 'detail.html')


@app.route("/list")
@auth.login_required
def list():
    cursor = get_db().cursor()
    list = db.list_participants(cursor)
    return jsonify(list)


@app.route("/screen/<int:participant_id>")
@auth.login_required
def screen(participant_id):
    path = f"{DATA_PREFIX}/{participant_id}/video/face.jpg"
    return send_file(path, mimetype='image/jpg')


@app.route("/segments/<int:participant_id>", methods=['GET', 'POST'])
@auth.login_required
def segments(participant_id):
    cursor = get_db().cursor()
    if request.method == 'GET':
        segments = db.get_participant_segments(cursor, participant_id)
        res = cursor.execute(
            """select complete,comment from participant where participant.id = ?""", [participant_id])
        complete, comment = res.fetchone()
        payload = {"segments": segments, "comment": comment, "complete": complete}
        return jsonify(payload)
    if request.method == 'POST':
        if "annotator" not in auth.current_user()["roles"]:
            return "Not allowed"
        data = request.form
        for dd in data:
            jd = json.loads(dd)
            print(jd)
            cursor.execute("REPLACE INTO participant(id, complete, comment) VALUES(?,?,?);",
                          (participant_id, jd["complete"], jd["comment"]))
            cursor.execute("DELETE from segments where participant_id = ?", [participant_id])
            for segment_k, segment_v in jd["segments"].items():
                print(segment_v)
                cursor.execute("""insert into segments(participant_id,start_time,end_time,label_id) 
                                values (?,?,?,(select id from segment_labels where name = ?))""",
                            [participant_id,segment_v["startTime"], segment_v["endTime"], segment_v["labelText"]]
                            )
        get_db().commit()
        return "OK"


def update_metadata(participant_id, completed, comment=""):
    db = get_db()
    cur = db.cursor()
    cur.execute("REPLACE INTO participant(id, complete, comment) VALUES(?,?,?);", (participant_id,completed,comment))
    db.commit()


@app.route("/participant/<int:participant_id>/<string:field>", methods=["POST"])
@auth.login_required(role='annotator')
def update_participant(participant_id, field):
    data = dict(request.form)
    db = get_db()
    cur = db.cursor()
    print(data)
    if field == "gender":
        print(data["value"])
        cur.execute(""" update participant SET gender=? WHERE id = ? """, [data["value"], participant_id])
        db.commit()
    elif field == "test":
        print(data["value"])
        cur.execute(""" update participant SET test=? WHERE id = ? """, [data["value"], participant_id])
        db.commit()
    #
    # res =
    return jsonify(["OK"])

@app.route("/segmentation/allowed")
@auth.login_required
def allowed_segments():
    cur = get_db().cursor()
    res = cur.execute("select name from segment_labels")
    return jsonify(res.fetchall())


@app.route('/video/<int:participant_id>')
@auth.login_required
def uploaded_file(participant_id):
    """Endpoint to serve uploaded videos
    Use `conditional=True` in order to support range requests necessary for
    seeking videos.
    """
    return send_from_directory(f"{DATA_PREFIX}/{participant_id}/video/", f"final.270p-15fps.mp4", conditional=True)

@app.route('/data/<filename>')
@auth.login_required
def data_file(filename):
    """Endpoint to serve uploaded videos
    Use `conditional=True` in order to support range requests necessary for
    seeking videos.
    """
    return send_from_directory(f"{DATA_PREFIX}/", f"{filename}", conditional=True)


@app.route('/export')
@auth.login_required
def export():
    out = []
    cursor = get_db().cursor()
    participants = db.list_participants(cursor)
    with open(f"{EXPORT_DIR}/participants.scp", "w") as fp:
        fp.write(f"participant_id;nsegs;complete;comment;gender;testset\n")
        for participant in participants:
            participant_id, nsegs, complete, comment, gender,testset = participant
            fp.write(f"{participant_id};{nsegs};{complete};{comment};{gender};{testset}\n")
            out.append(f"{participant_id};{nsegs};{complete};{comment};{gender};{testset}\n")
            with open(f"{EXPORT_DIR}/{participant_id}.segments", "w") as fps:
                participant_segments = db.get_participant_segments(cursor, participant_id)
                fps.write("start;end;name\n")
                for seg_name,seg_start,seg_end in participant_segments:
                    fps.write(f"{seg_start};{seg_end};{seg_name}\n")
                print(participant_segments)
    print(out)
    return f"Export done into {EXPORT_DIR}"
