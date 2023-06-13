CREATE TABLE participant (id integer PRIMARY KEY , complete bool, comment text, gender text, test bool DEFAULT false);
CREATE TABLE segment_labels (id integer PRIMARY KEY AUTOINCREMENT NOT NULL, name text, color text);
CREATE TABLE segments (id integer PRIMARY KEY AUTOINCREMENT NOT NULL, participant_id REFERENCES participant(id) NOT NULL , label_id REFERENCES segment_labels(id) NOT NULL , start_time real NOT NULL , end_time real NOT NULL );

INSERT INTO segment_labels(name) VALUES ("Instructions");
INSERT INTO segment_labels(name) VALUES ("PSS14");
INSERT INTO segment_labels(name) VALUES ("STAI-Y2");
INSERT INTO segment_labels(name) VALUES ("Relax");
INSERT INTO segment_labels(name) VALUES ("Water");
INSERT INTO segment_labels(name) VALUES ("Rebus");
INSERT INTO segment_labels(name) VALUES ("Rebus2");
INSERT INTO segment_labels(name) VALUES ("NASA-TLX");
INSERT INTO segment_labels(name) VALUES ("Debriefing");
