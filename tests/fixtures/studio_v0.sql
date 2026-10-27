-- Last unversioned Studio layout, independent of the new migration implementation.
CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE preferences(id INTEGER PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE messages(id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),role TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL,metrics TEXT);
CREATE TABLE goals(id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),objective TEXT NOT NULL,status TEXT NOT NULL,steps TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL);
CREATE TABLE tasks(id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),mode TEXT NOT NULL,status TEXT NOT NULL,model TEXT NOT NULL,created REAL NOT NULL,result TEXT,goal TEXT REFERENCES goals(id),profile TEXT NOT NULL DEFAULT 'unified');
CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,task TEXT NOT NULL REFERENCES tasks(id),kind TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL);
CREATE INDEX events_task_kind_seq ON events(task,kind,seq);
CREATE TABLE verifications(id TEXT PRIMARY KEY,task TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,payload TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE attachments(id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),message TEXT REFERENCES messages(id),name TEXT NOT NULL,mime TEXT NOT NULL,data BLOB NOT NULL,text TEXT,size INTEGER NOT NULL);
