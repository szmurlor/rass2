ALTER TABLE stored_file ADD token TEXT NULL;


CREATE TABLE processing_task (
	id INTEGER NOT NULL, 
	"key" VARCHAR(128), 
	storedfile_1_id INTEGER, 
	storedfile_2_id INTEGER, 
	status VARCHAR(128), 
	processing_meta VARCHAR(1024), 
	date_created DATETIME, 
	user_created_id INTEGER, 
	date_modified DATETIME, 
	date_requested DATETIME, 
	taskdata VARCHAR(8192), 
	PRIMARY KEY (id), 
	FOREIGN KEY(storedfile_1_id) REFERENCES stored_file (uid), 
	FOREIGN KEY(storedfile_2_id) REFERENCES stored_file (uid), 
	FOREIGN KEY(user_created_id) REFERENCES user (id)
);
