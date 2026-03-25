CREATE TABLE customers (
	id VARCHAR(100) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);


CREATE TABLE products (
	id VARCHAR(100) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	sku VARCHAR(100) NOT NULL, 
	description TEXT, 
	unit_price FLOAT NOT NULL, 
	stock_quantity INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);


CREATE TABLE addresses (
	id VARCHAR(100) NOT NULL, 
	customer_id VARCHAR(100) NOT NULL, 
	address_type VARCHAR(20), 
	street VARCHAR(255) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	state VARCHAR(100), 
	postal_code VARCHAR(20), 
	country VARCHAR(100) NOT NULL, 
	is_default INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);


CREATE TABLE orders (
	id VARCHAR(100) NOT NULL, 
	customer_id VARCHAR(100) NOT NULL, 
	shipping_address_id VARCHAR(100), 
	billing_address_id VARCHAR(100), 
	order_date DATETIME, 
	status VARCHAR(50), 
	total_amount FLOAT, 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(shipping_address_id) REFERENCES addresses (id), 
	FOREIGN KEY(billing_address_id) REFERENCES addresses (id)
);


CREATE TABLE deliveries (
	id VARCHAR(100) NOT NULL, 
	order_id VARCHAR(100) NOT NULL, 
	status VARCHAR(50), 
	shipped_date DATETIME, 
	delivered_date DATETIME, 
	tracking_number VARCHAR(255), 
	carrier VARCHAR(100), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	UNIQUE (tracking_number)
);


CREATE TABLE order_items (
	id VARCHAR(100) NOT NULL, 
	order_id VARCHAR(100) NOT NULL, 
	product_id VARCHAR(100) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price FLOAT NOT NULL, 
	total_price FLOAT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_order_product UNIQUE (order_id, product_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(product_id) REFERENCES products (id)
);


CREATE TABLE invoices (
	id VARCHAR(100) NOT NULL, 
	delivery_id VARCHAR(100) NOT NULL, 
	invoice_number VARCHAR(100) NOT NULL, 
	invoice_date DATETIME, 
	due_date DATE, 
	total_amount FLOAT NOT NULL, 
	status VARCHAR(50), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(delivery_id) REFERENCES deliveries (id)
);


CREATE TABLE payments (
	id VARCHAR(100) NOT NULL, 
	invoice_id VARCHAR(100) NOT NULL, 
	payment_date DATETIME, 
	amount FLOAT NOT NULL, 
	method VARCHAR(50) NOT NULL, 
	transaction_ref VARCHAR(255), 
	status VARCHAR(50), 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	UNIQUE (transaction_ref)
);

