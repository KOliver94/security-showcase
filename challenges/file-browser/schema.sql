DROP TABLE IF EXISTS users;

CREATE TABLE users
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT        NOT NULL
);

INSERT INTO users (username, password)
VALUES ('admin', 'scrypt:32768:8:1$gj2KCCzObDFlTalK$e3ca2eabd4a054ef44f273ce60758a444dbf533f21d3649e51fc2959275da91ef17c8f224c95c27e013101653075fb3b797c9892d91cdf0d8a5680850b2a8592');
