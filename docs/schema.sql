-- Схема БД (PostgreSQL). Згенеровано з app/models.py

CREATE TABLE categories (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_users_role CHECK (role IN ('client','master')), 
	UNIQUE (email)
);

CREATE TABLE masters (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	bio TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id)
);

CREATE INDEX ix_masters_city_category ON masters (city, category_id);

CREATE TABLE services (
	id SERIAL NOT NULL, 
	master_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	price INTEGER NOT NULL, 
	duration_min INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_services_price CHECK (price > 0), 
	CONSTRAINT ck_services_duration CHECK (duration_min > 0), 
	FOREIGN KEY(master_id) REFERENCES masters (id)
);

CREATE INDEX ix_services_master_id ON services (master_id);

CREATE TABLE work_schedule (
	id SERIAL NOT NULL, 
	master_id INTEGER NOT NULL, 
	weekday INTEGER NOT NULL, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_schedule_master_weekday UNIQUE (master_id, weekday), 
	CONSTRAINT ck_schedule_weekday CHECK (weekday BETWEEN 0 AND 6), 
	CONSTRAINT ck_schedule_time CHECK (start_time < end_time), 
	FOREIGN KEY(master_id) REFERENCES masters (id)
);

CREATE TABLE bookings (
	id SERIAL NOT NULL, 
	client_id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	master_id INTEGER NOT NULL, 
	start_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	end_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_bookings_status CHECK (status IN ('booked','cancelled')), 
	CONSTRAINT ck_bookings_time CHECK (end_at > start_at), 
	FOREIGN KEY(client_id) REFERENCES users (id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(master_id) REFERENCES masters (id)
);

CREATE INDEX ix_bookings_service_id ON bookings (service_id);

CREATE INDEX ix_bookings_client_id ON bookings (client_id);

CREATE UNIQUE INDEX uq_booking_active_slot ON bookings (master_id, start_at) WHERE status = 'booked';

CREATE TABLE reviews (
	id SERIAL NOT NULL, 
	booking_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	text TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_reviews_rating CHECK (rating BETWEEN 1 AND 5), 
	UNIQUE (booking_id), 
	FOREIGN KEY(booking_id) REFERENCES bookings (id)
);
