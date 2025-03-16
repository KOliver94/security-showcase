DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS posts;

CREATE TABLE users
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT        NOT NULL,
    is_admin BOOLEAN     NOT NULL DEFAULT false
);

CREATE TABLE posts
(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER   NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title   TEXT      NOT NULL,
    body    TEXT      NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

INSERT INTO users (username, password, is_admin)
VALUES ('admin', '2251770cd912f585f675d34532c8a1f5', 1),
       ('johndoe', '202cb962ac59075b964b07152d234b70', 0),
       ('janedoe', '5f4dcc3b5aa765d61d8327deb882cf99', 0),
       ('alice', 'e99a18c428cb38d5f260853678922e03', 0),
       ('bob', 'd8578edf8458ce06fbc5bb76a58c5ca4', 0),
       ('charlie', '55408f908a3afa91c382a0ffbf1c4efc', 1),
       ('david', '4ac373bdcba632c46fc78e145cffb4d6', 0),
       ('eve', '4b1bac09fb9478d0f24426183d7b5f02', 1);


INSERT INTO posts (user_id, title, body)
VALUES (1, 'Welcome to Our New Employees!',
        'We are excited to welcome our newest team members to the company! Please take a moment to introduce yourself in the team chat.'),
       (2, 'Quarterly All-Hands Meeting',
        'Our next all-hands meeting is scheduled for March 15th at 10 AM. We will discuss company updates, upcoming projects, and answer your questions.'),
       (3, 'New Remote Work Policy',
        'Starting next month, employees will have the option to work remotely up to three days a week. Check your email for full details.'),
       (4, 'Security Reminder: Enable Two-Factor Authentication',
        'To keep our data secure, we strongly encourage everyone to enable two-factor authentication on their accounts.'),
       (5, 'Upcoming Maintenance Downtime',
        'Our IT team will be performing scheduled maintenance on the internal servers this Saturday from 12 AM to 4 AM. Services may be temporarily unavailable.'),
       (1, 'Congratulations to Our Employee of the Month!',
        'A big shoutout to Alice for her outstanding contributions this month. Keep up the great work!'),
       (2, 'Office Renovations Next Week',
        'We will be renovating the break room and common areas starting Monday. Expect some temporary disruptions.'),
       (3, 'Health & Wellness Program Launch',
        'We are launching a new wellness initiative, including yoga sessions and mental health resources. More details coming soon!'),
       (4, 'Internal Hackathon: Sign Up Now!',
        'We are hosting an internal hackathon next month! Teams will compete to create innovative solutions to real-world problems.'),
       (5, 'New Learning & Development Portal',
        'We have launched a new internal learning portal where you can access training materials and professional development courses.');

