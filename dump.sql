/*
In Neon, databases are stored on branches. By default, a project has one branch and one database.
You can select the branch and database to use from the drop-down menus above.

Try generating sample data and querying it by running the example statements below, or click
New Query to clear the editor.
*/
DROP SCHEMA IF EXISTS TikTakTuk CASCADE;
CREATE SCHEMA TikTakTuk;

SET search_path TO TikTakTuk, public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE user_account (
    user_id UUID PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE role (
    role_id UUID PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE account_role (
    role_id UUID,
    user_id UUID,
    PRIMARY KEY (role_id, user_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
);

CREATE TABLE customer (
    customer_id UUID PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    user_id UUID UNIQUE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
);

CREATE TABLE organizer (
    organizer_id UUID PRIMARY KEY,
    organizer_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100),
    user_id UUID UNIQUE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
);

CREATE TABLE venue (
    venue_id UUID PRIMARY KEY,
    venue_name VARCHAR(100) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL
);

CREATE TABLE seat (
    seat_id UUID PRIMARY KEY,
    section VARCHAR(50) NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    row_number VARCHAR(10) NOT NULL,
    venue_id UUID NOT NULL,
    FOREIGN KEY (venue_id) REFERENCES venue(venue_id)
);

CREATE TABLE artist (
    artist_id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    genre VARCHAR(100)
);

CREATE TABLE event (
    event_id UUID PRIMARY KEY,
    event_datetime TIMESTAMP NOT NULL,
    event_title VARCHAR(200) NOT NULL,
    venue_id UUID NOT NULL,
    organizer_id UUID NOT NULL,
    FOREIGN KEY (venue_id) REFERENCES venue(venue_id),
    FOREIGN KEY (organizer_id) REFERENCES organizer(organizer_id)
);

CREATE TABLE event_artist (
    event_id UUID,
    artist_id UUID,
    role VARCHAR(100),
    PRIMARY KEY (event_id, artist_id),
    FOREIGN KEY (event_id) REFERENCES event(event_id),
    FOREIGN KEY (artist_id) REFERENCES artist(artist_id)
);

CREATE TABLE ticket_category (
    category_id UUID PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    quota INTEGER NOT NULL CHECK (quota > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    event_id UUID NOT NULL,
    FOREIGN KEY (event_id) REFERENCES event(event_id)
);

CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    order_date TIMESTAMP NOT NULL,
    payment_status VARCHAR(20) NOT NULL,
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    customer_id UUID NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE promotion (
    promotion_id UUID PRIMARY KEY,
    promo_code VARCHAR(50) UNIQUE NOT NULL,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('NOMINAL','PERCENTAGE')),
    discount_value NUMERIC(12,2) NOT NULL CHECK (discount_value > 0),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    usage_limit INTEGER NOT NULL CHECK (usage_limit > 0)
);

CREATE TABLE order_promotion (
    order_promotion_id UUID PRIMARY KEY,
    promotion_id UUID NOT NULL,
    order_id UUID NOT NULL,
    FOREIGN KEY (promotion_id) REFERENCES promotion(promotion_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE ticket (
    ticket_id UUID PRIMARY KEY,
    ticket_code VARCHAR(100) UNIQUE NOT NULL,
    tcategory_id UUID NOT NULL,
    torder_id UUID NOT NULL,
    FOREIGN KEY (tcategory_id) REFERENCES ticket_category(category_id),
    FOREIGN KEY (torder_id) REFERENCES orders(order_id)
);

CREATE TABLE has_relationship (
    seat_id UUID,
    ticket_id UUID,
    PRIMARY KEY (seat_id, ticket_id),
    FOREIGN KEY (seat_id) REFERENCES seat(seat_id),
    FOREIGN KEY (ticket_id) REFERENCES ticket(ticket_id)
);

-- =========================
-- DUMMY DATA
-- =========================


-- Aktifin generator UUID (Postgres)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

BEGIN;

-- ==========================================
-- 1. ROLE (3 data)
-- ==========================================
INSERT INTO role (role_id, role_name) VALUES 
(gen_random_uuid(), 'ADMIN'),
(gen_random_uuid(), 'ORGANIZER'),
(gen_random_uuid(), 'CUSTOMER');

-- ==========================================
-- 2. USER_ACCOUNT (12 data)
-- ==========================================
INSERT INTO user_account (user_id, username, password) VALUES
(gen_random_uuid(), 'admin_utama', 'pass_admin'),
(gen_random_uuid(), 'israya_live', 'pass_org1'),
(gen_random_uuid(), 'dyandra_ent', 'pass_org2'),
(gen_random_uuid(), 'pk_ent', 'pass_org3'),
(gen_random_uuid(), 'mecima_pro', 'pass_org4'),
(gen_random_uuid(), 'rinaldi_putra', 'pass_cust1'),
(gen_random_uuid(), 'sari_puspa', 'pass_cust2'),
(gen_random_uuid(), 'budi_santoso', 'pass_cust3'),
(gen_random_uuid(), 'denny_setiawan', 'pass_cust4'),
(gen_random_uuid(), 'anita_wijaya', 'pass_cust5'),
(gen_random_uuid(), 'fajar_hidayat', 'pass_cust6'),
(gen_random_uuid(), 'admin_dua', 'pass_admin2');

-- ==========================================
-- 3. ACCOUNT_ROLE (Relasi lewat Subquery)
-- ==========================================
INSERT INTO account_role (role_id, user_id)
SELECT (SELECT role_id FROM role WHERE role_name = 'ADMIN'), user_id FROM user_account WHERE username LIKE 'admin%';

INSERT INTO account_role (role_id, user_id)
SELECT (SELECT role_id FROM role WHERE role_name = 'ORGANIZER'), user_id FROM user_account WHERE username IN ('israya_live', 'dyandra_ent', 'pk_ent', 'mecima_pro');

INSERT INTO account_role (role_id, user_id)
SELECT (SELECT role_id FROM role WHERE role_name = 'CUSTOMER'), user_id FROM user_account WHERE username NOT LIKE 'admin%' AND username NOT IN ('israya_live', 'dyandra_ent', 'pk_ent', 'mecima_pro');

-- ==========================================
-- 4. CUSTOMER & ORGANIZER
-- ==========================================
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Rinaldi Putra', '08123', user_id FROM user_account WHERE username = 'rinaldi_putra';
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Sari Puspa', '08124', user_id FROM user_account WHERE username = 'sari_puspa';
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Budi Santoso', '08125', user_id FROM user_account WHERE username = 'budi_santoso';
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Denny Setiawan', '08126', user_id FROM user_account WHERE username = 'denny_setiawan';
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Anita Wijaya', '08127', user_id FROM user_account WHERE username = 'anita_wijaya';
INSERT INTO customer (customer_id, full_name, phone_number, user_id)
SELECT gen_random_uuid(), 'Fajar Hidayat', '08128', user_id FROM user_account WHERE username = 'fajar_hidayat';

INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id)
SELECT gen_random_uuid(), 'Israya Live', 'info@israya.com', user_id FROM user_account WHERE username = 'israya_live';
INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id)
SELECT gen_random_uuid(), 'Dyandra Entertainment', 'info@dyandra.com', user_id FROM user_account WHERE username = 'dyandra_ent';
INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id)
SELECT gen_random_uuid(), 'PK Entertainment', 'info@pk.com', user_id FROM user_account WHERE username = 'pk_ent';
INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id)
SELECT gen_random_uuid(), 'Mecima Pro', 'info@mecima.com', user_id FROM user_account WHERE username = 'mecima_pro';

-- ==========================================
-- 5. VENUE (5 data)
-- ==========================================
INSERT INTO venue (venue_id, venue_name, capacity, address, city) VALUES
(gen_random_uuid(), 'Stadion Utama GBK', 77000, 'Senayan', 'Jakarta'),
(gen_random_uuid(), 'ICE BSD', 10000, 'BSD City', 'Tangerang'),
(gen_random_uuid(), 'Jakarta International Stadium', 82000, 'Sunter', 'Jakarta'),
(gen_random_uuid(), 'Tennis Indoor', 3300, 'Senayan', 'Jakarta'),
(gen_random_uuid(), 'Beach City Stadium', 15000, 'Ancol', 'Jakarta');

-- ==========================================
-- 6. SEAT (30 data - Loop manual simpel)
-- ==========================================
-- Masukin 30 seat ke GBK sebagai contoh
INSERT INTO seat (seat_id, section, seat_number, row_number, venue_id)
SELECT gen_random_uuid(), 'CAT 1', i::text, 'A', (SELECT venue_id FROM venue WHERE venue_name = 'Stadion Utama GBK')
FROM generate_series(1, 30) AS i;

-- ==========================================
-- 7. ARTIST (8 data)
-- ==========================================
INSERT INTO artist (artist_id, name, genre) VALUES
(gen_random_uuid(), 'Coldplay', 'Rock'),
(gen_random_uuid(), 'NewJeans', 'K-Pop'),
(gen_random_uuid(), 'Tulus', 'Pop'),
(gen_random_uuid(), 'Sheila on 7', 'Pop Rock'),
(gen_random_uuid(), 'Bruno Mars', 'Pop'),
(gen_random_uuid(), 'Wave to Earth', 'Indie'),
(gen_random_uuid(), 'Hindia', 'Indie'),
(gen_random_uuid(), 'Yoasobi', 'J-Pop');

-- ==========================================
-- 8. EVENT (6 data)
-- ==========================================
INSERT INTO event (event_id, event_datetime, event_title, venue_id, organizer_id) VALUES
(gen_random_uuid(), '2026-05-15 19:00:00', 'Coldplay Jakarta', (SELECT venue_id FROM venue WHERE venue_name = 'Stadion Utama GBK'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'PK Entertainment')),
(gen_random_uuid(), '2026-06-20 18:30:00', 'NewJeans Fanmeet', (SELECT venue_id FROM venue WHERE venue_name = 'ICE BSD'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'Mecima Pro')),
(gen_random_uuid(), '2026-07-10 20:00:00', 'Tulus Tur', (SELECT venue_id FROM venue WHERE venue_name = 'Tennis Indoor'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'Dyandra Entertainment')),
(gen_random_uuid(), '2026-08-05 19:30:00', 'SO7 Concert', (SELECT venue_id FROM venue WHERE venue_name = 'Jakarta International Stadium'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'Israya Live')),
(gen_random_uuid(), '2026-09-12 19:00:00', 'Bruno Mars Tour', (SELECT venue_id FROM venue WHERE venue_name = 'Jakarta International Stadium'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'PK Entertainment')),
(gen_random_uuid(), '2026-10-25 17:00:00', 'Indie Fest', (SELECT venue_id FROM venue WHERE venue_name = 'Beach City Stadium'), (SELECT organizer_id FROM organizer WHERE organizer_name = 'Israya Live'));

-- ==========================================
-- 9. EVENT_ARTIST (12 data)
-- ==========================================
-- Mapping artist ke event lewat subquery
INSERT INTO event_artist (event_id, artist_id, role) VALUES
((SELECT event_id FROM event WHERE event_title = 'Coldplay Jakarta'), (SELECT artist_id FROM artist WHERE name = 'Coldplay'), 'Main'),
((SELECT event_id FROM event WHERE event_title = 'NewJeans Fanmeet'), (SELECT artist_id FROM artist WHERE name = 'NewJeans'), 'Main'),
((SELECT event_id FROM event WHERE event_title = 'Tulus Tur'), (SELECT artist_id FROM artist WHERE name = 'Tulus'), 'Main'),
((SELECT event_id FROM event WHERE event_title = 'SO7 Concert'), (SELECT artist_id FROM artist WHERE name = 'Sheila on 7'), 'Main'),
((SELECT event_id FROM event WHERE event_title = 'Bruno Mars Tour'), (SELECT artist_id FROM artist WHERE name = 'Bruno Mars'), 'Main'),
((SELECT event_id FROM event WHERE event_title = 'Indie Fest'), (SELECT artist_id FROM artist WHERE name = 'Wave to Earth'), 'Headline'),
((SELECT event_id FROM event WHERE event_title = 'Indie Fest'), (SELECT artist_id FROM artist WHERE name = 'Hindia'), 'Guest'),
((SELECT event_id FROM event WHERE event_title = 'Coldplay Jakarta'), (SELECT artist_id FROM artist WHERE name = 'Tulus'), 'Opening'),
((SELECT event_id FROM event WHERE event_title = 'NewJeans Fanmeet'), (SELECT artist_id FROM artist WHERE name = 'Yoasobi'), 'Guest'),
((SELECT event_id FROM event WHERE event_title = 'Indie Fest'), (SELECT artist_id FROM artist WHERE name = 'Sheila on 7'), 'Special'),
((SELECT event_id FROM event WHERE event_title = 'Bruno Mars Tour'), (SELECT artist_id FROM artist WHERE name = 'NewJeans'), 'Special Guest'),
((SELECT event_id FROM event WHERE event_title = 'SO7 Concert'), (SELECT artist_id FROM artist WHERE name = 'Hindia'), 'Guest');

-- ==========================================
-- 10. TICKET_CATEGORY (14 data)
-- ==========================================
INSERT INTO ticket_category (category_id, category_name, quota, price, event_id)
SELECT gen_random_uuid(), 'VIP', 100, 5000000, event_id FROM event LIMIT 6;
INSERT INTO ticket_category (category_id, category_name, quota, price, event_id)
SELECT gen_random_uuid(), 'CAT 1', 200, 2500000, event_id FROM event LIMIT 6;
INSERT INTO ticket_category (category_id, category_name, quota, price, event_id)
SELECT gen_random_uuid(), 'Festival', 500, 1500000, event_id FROM event LIMIT 2;

-- ==========================================
-- 11. PROMOTION (6 data)
-- ==========================================
INSERT INTO promotion (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit) VALUES
(gen_random_uuid(), 'PROMO10', 'PERCENTAGE', 10, '2026-01-01', '2026-12-31', 100),
(gen_random_uuid(), 'DISKON100K', 'NOMINAL', 100000, '2026-01-01', '2026-12-31', 50),
(gen_random_uuid(), 'GAJIAN', 'PERCENTAGE', 5, '2026-01-01', '2026-12-31', 200),
(gen_random_uuid(), 'FESTIVALSERU', 'PERCENTAGE', 20, '2026-01-01', '2026-12-31', 30),
(gen_random_uuid(), 'HEBATS7', 'NOMINAL', 50000, '2026-01-01', '2026-12-31', 1000),
(gen_random_uuid(), 'VIPONLY', 'PERCENTAGE', 15, '2026-01-01', '2026-12-31', 20);

-- ==========================================
-- 12. ORDERS (12 data)
-- ==========================================
INSERT INTO orders (order_id, order_date, payment_status, total_amount, customer_id)
SELECT gen_random_uuid(), now(), 'PAID', 5000000, customer_id FROM customer CROSS JOIN generate_series(1,2);

-- ==========================================
-- 13. ORDER_PROMOTION (5 data)
-- ==========================================
INSERT INTO order_promotion (order_promotion_id, promotion_id, order_id)
SELECT gen_random_uuid(), (SELECT promotion_id FROM promotion LIMIT 1), order_id FROM orders LIMIT 5;

-- ==========================================
-- 14. TICKET (20 data)
-- ==========================================
INSERT INTO ticket (ticket_id, ticket_code, tcategory_id, torder_id)
SELECT gen_random_uuid(), 'TCK-' || floor(random()*1000000)::text, (SELECT category_id FROM ticket_category LIMIT 1), order_id 
FROM orders CROSS JOIN generate_series(1, 2) LIMIT 20;

-- ==========================================
-- 15. HAS_RELATIONSHIP (20 data)
-- ==========================================
-- Mapping seat ke ticket (kita ambil seat dari GBK aja buat contoh)
INSERT INTO has_relationship (seat_id, ticket_id)
SELECT s.seat_id, t.ticket_id 
FROM (SELECT seat_id, row_number() OVER () as rn FROM seat LIMIT 20) s
JOIN (SELECT ticket_id, row_number() OVER () as rn FROM ticket LIMIT 20) t ON s.rn = t.rn;

COMMIT;