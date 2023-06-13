import sqlite3

def connect(db_file):
    return sqlite3.connect(db_file)

def list_participants(cursor):
    res = cursor.execute(
        """select participant.id,(select count(*) from segments where participant_id=participant.id) as ndone,complete,comment,gender,test from participant order by ndone desc""")
    return res.fetchall()

def get_participant_segments(cursor, participant_id):
    res = cursor.execute(
        """select 
            (select name from segment_labels where segment_labels.id=segments.label_id)
            ,start_time
            ,end_time from segments where participant_id= ?""",
        [participant_id])
    return res.fetchall()

