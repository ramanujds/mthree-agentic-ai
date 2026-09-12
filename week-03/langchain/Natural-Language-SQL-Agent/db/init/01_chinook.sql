-- A small Chinook-style digital media store schema (artists, albums, tracks,
-- customers, invoices, invoice_items) for the natural-language SQL agent demo.
-- Loaded automatically by the postgres image on first container start.

CREATE TABLE artists (
    artist_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE genres (
    genre_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE albums (
    album_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    artist_id INTEGER NOT NULL REFERENCES artists(artist_id),
    release_year INTEGER
);

CREATE TABLE tracks (
    track_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    album_id INTEGER REFERENCES albums(album_id),
    genre_id INTEGER REFERENCES genres(genre_id),
    milliseconds INTEGER NOT NULL,
    unit_price NUMERIC(5, 2) NOT NULL
);

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    country VARCHAR(100) NOT NULL
);

CREATE TABLE invoices (
    invoice_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    invoice_date DATE NOT NULL,
    billing_country VARCHAR(100) NOT NULL,
    total NUMERIC(10, 2) NOT NULL
);

CREATE TABLE invoice_items (
    invoice_item_id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id),
    track_id INTEGER NOT NULL REFERENCES tracks(track_id),
    unit_price NUMERIC(5, 2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1
);

-- Artists
INSERT INTO artists (artist_id, name) VALUES
    (1, 'Queen'),
    (2, 'Pink Floyd'),
    (3, 'AC/DC'),
    (4, 'Radiohead'),
    (5, 'Daft Punk'),
    (6, 'Miles Davis'),
    (7, 'Nirvana'),
    (8, 'Fleetwood Mac'),
    (9, 'Beyonce'),
    (10, 'Metallica');

-- Genres
INSERT INTO genres (genre_id, name) VALUES
    (1, 'Rock'),
    (2, 'Jazz'),
    (3, 'Electronic'),
    (4, 'Grunge'),
    (5, 'Pop'),
    (6, 'Metal');

-- Albums
INSERT INTO albums (album_id, title, artist_id, release_year) VALUES
    (1, 'A Night at the Opera', 1, 1975),
    (2, 'News of the World', 1, 1977),
    (3, 'The Dark Side of the Moon', 2, 1973),
    (4, 'Wish You Were Here', 2, 1975),
    (5, 'Back in Black', 3, 1980),
    (6, 'Highway to Hell', 3, 1979),
    (7, 'OK Computer', 4, 1997),
    (8, 'In Rainbows', 4, 2007),
    (9, 'Discovery', 5, 2001),
    (10, 'Random Access Memories', 5, 2013),
    (11, 'Kind of Blue', 6, 1959),
    (12, 'Nevermind', 7, 1991),
    (13, 'Rumours', 8, 1977),
    (14, 'Renaissance', 9, 2022),
    (15, 'Master of Puppets', 10, 1986);

-- Tracks (1-30 priced at 0.99, 31-40 at 1.29)
INSERT INTO tracks (track_id, name, album_id, genre_id, milliseconds, unit_price) VALUES
    (1, 'Bohemian Rhapsody', 1, 1, 354000, 0.99),
    (2, 'Love of My Life', 1, 1, 219000, 0.99),
    (3, 'We Are the Champions', 2, 1, 179000, 0.99),
    (4, 'We Will Rock You', 2, 1, 122000, 0.99),
    (5, 'Time', 3, 1, 421000, 0.99),
    (6, 'Money', 3, 1, 382000, 0.99),
    (7, 'Us and Them', 3, 1, 429000, 0.99),
    (8, 'Wish You Were Here', 4, 1, 334000, 0.99),
    (9, 'Shine On You Crazy Diamond', 4, 1, 810000, 0.99),
    (10, 'Hells Bells', 5, 1, 312000, 0.99),
    (11, 'You Shook Me All Night Long', 5, 1, 210000, 0.99),
    (12, 'Back in Black', 5, 1, 255000, 0.99),
    (13, 'Highway to Hell', 6, 1, 208000, 0.99),
    (14, 'Girls Got Rhythm', 6, 1, 236000, 0.99),
    (15, 'Paranoid Android', 7, 1, 383000, 0.99),
    (16, 'Karma Police', 7, 1, 264000, 0.99),
    (17, 'No Surprises', 7, 1, 229000, 0.99),
    (18, 'Exit Music (For a Film)', 7, 1, 264000, 0.99),
    (19, '15 Step', 8, 1, 237000, 0.99),
    (20, 'Bodysnatchers', 8, 1, 242000, 0.99),
    (21, 'Nude', 8, 1, 254000, 0.99),
    (22, 'One More Time', 9, 3, 320000, 0.99),
    (23, 'Digital Love', 9, 3, 300000, 0.99),
    (24, 'Harder Better Faster Stronger', 9, 3, 224000, 0.99),
    (25, 'Get Lucky', 10, 3, 369000, 0.99),
    (26, 'Instant Crush', 10, 3, 337000, 0.99),
    (27, 'So What', 11, 2, 545000, 0.99),
    (28, 'Freddie Freeloader', 11, 2, 585000, 0.99),
    (29, 'Blue in Green', 11, 2, 337000, 0.99),
    (30, 'All Blues', 11, 2, 693000, 0.99),
    (31, 'Smells Like Teen Spirit', 12, 4, 301000, 1.29),
    (32, 'Come As You Are', 12, 4, 219000, 1.29),
    (33, 'Lithium', 12, 4, 257000, 1.29),
    (34, 'In Bloom', 12, 4, 254000, 1.29),
    (35, 'Dreams', 13, 5, 257000, 1.29),
    (36, 'Go Your Own Way', 13, 5, 217000, 1.29),
    (37, 'The Chain', 13, 1, 268000, 1.29),
    (38, 'Alien Superstar', 14, 5, 180000, 1.29),
    (39, 'Break My Soul', 14, 5, 279000, 1.29),
    (40, 'Battery', 15, 6, 312000, 1.29);

-- Customers
INSERT INTO customers (customer_id, first_name, last_name, email, country) VALUES
    (1, 'Alice', 'Johnson', 'alice.johnson@example.com', 'USA'),
    (2, 'Bob', 'Smith', 'bob.smith@example.com', 'Canada'),
    (3, 'Carla', 'Diaz', 'carla.diaz@example.com', 'Spain'),
    (4, 'David', 'Lee', 'david.lee@example.com', 'South Korea'),
    (5, 'Emma', 'Brown', 'emma.brown@example.com', 'UK'),
    (6, 'Farid', 'Haidari', 'farid.haidari@example.com', 'UAE'),
    (7, 'Grace', 'Kim', 'grace.kim@example.com', 'South Korea'),
    (8, 'Hiro', 'Tanaka', 'hiro.tanaka@example.com', 'Japan');

-- Invoices (total = sum of the matching invoice_items below)
INSERT INTO invoices (invoice_id, customer_id, invoice_date, billing_country, total) VALUES
    (1, 1, '2024-01-05', 'USA', 2.97),
    (2, 2, '2024-01-10', 'Canada', 2.58),
    (3, 3, '2024-01-15', 'Spain', 2.97),
    (4, 1, '2024-02-02', 'USA', 3.96),
    (5, 4, '2024-02-08', 'South Korea', 1.29),
    (6, 5, '2024-02-20', 'UK', 1.98),
    (7, 2, '2024-03-01', 'Canada', 2.97),
    (8, 6, '2024-03-05', 'UAE', 3.57),
    (9, 7, '2024-03-15', 'South Korea', 2.97),
    (10, 1, '2024-04-01', 'USA', 2.58),
    (11, 8, '2024-04-10', 'Japan', 1.98),
    (12, 3, '2024-04-18', 'Spain', 2.97);

-- Invoice items
INSERT INTO invoice_items (invoice_id, track_id, unit_price, quantity) VALUES
    (1, 3, 0.99, 1), (1, 7, 0.99, 1), (1, 12, 0.99, 1),
    (2, 31, 1.29, 1), (2, 32, 1.29, 1),
    (3, 1, 0.99, 2), (3, 5, 0.99, 1),
    (4, 15, 0.99, 1), (4, 16, 0.99, 1), (4, 17, 0.99, 1), (4, 18, 0.99, 1),
    (5, 33, 1.29, 1),
    (6, 20, 0.99, 1), (6, 21, 0.99, 1),
    (7, 25, 0.99, 3),
    (8, 35, 1.29, 2), (8, 8, 0.99, 1),
    (9, 2, 0.99, 1), (9, 4, 0.99, 1), (9, 6, 0.99, 1),
    (10, 40, 1.29, 1), (10, 39, 1.29, 1),
    (11, 10, 0.99, 1), (11, 11, 0.99, 1),
    (12, 22, 0.99, 1), (12, 23, 0.99, 1), (12, 24, 0.99, 1);

-- Keep SERIAL sequences ahead of the explicit ids inserted above.
SELECT setval('artists_artist_id_seq', (SELECT MAX(artist_id) FROM artists));
SELECT setval('genres_genre_id_seq', (SELECT MAX(genre_id) FROM genres));
SELECT setval('albums_album_id_seq', (SELECT MAX(album_id) FROM albums));
SELECT setval('tracks_track_id_seq', (SELECT MAX(track_id) FROM tracks));
SELECT setval('customers_customer_id_seq', (SELECT MAX(customer_id) FROM customers));
SELECT setval('invoices_invoice_id_seq', (SELECT MAX(invoice_id) FROM invoices));
SELECT setval('invoice_items_invoice_item_id_seq', (SELECT MAX(invoice_item_id) FROM invoice_items));
