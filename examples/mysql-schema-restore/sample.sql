CREATE DATABASE catalog_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE catalog_demo;

CREATE TABLE categories (
  id INT PRIMARY KEY,
  label VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE items (
  id INT PRIMARY KEY,
  category_id INT NOT NULL,
  label VARCHAR(100) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  note TEXT NULL,
  added_on DATE NOT NULL,
  CONSTRAINT fk_item_category FOREIGN KEY (category_id) REFERENCES categories(id),
  INDEX idx_item_label (label)
) ENGINE=InnoDB;

CREATE TABLE import_audit (
  item_id INT PRIMARY KEY,
  message VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

INSERT INTO categories VALUES (1, 'Stationery'), (2, '文具 📚');
INSERT INTO items VALUES
  (1, 1, 'Notebook', 12.50, NULL, '2026-10-01'),
  (2, 2, '鉛筆 ✏️', 0.75, 'line one\nline two', '2026-10-02'),
  (3, 1, 'Apostrophe '' and backslash \\', 0.00, '', '2026-10-03');

CREATE VIEW item_summary AS
SELECT items.id, categories.label AS category, items.label, items.price
FROM items JOIN categories ON categories.id = items.category_id;

DELIMITER //
CREATE PROCEDURE item_count()
BEGIN
  SELECT COUNT(*) AS total FROM items;
END//

CREATE TRIGGER item_insert_audit AFTER INSERT ON items
FOR EACH ROW
BEGIN
  INSERT INTO import_audit VALUES (NEW.id, CONCAT('Added: ', NEW.label));
END//

CREATE EVENT future_marker
ON SCHEDULE AT '2030-01-01 00:00:00'
DISABLE
DO
BEGIN
  INSERT INTO import_audit VALUES (9999, 'Scheduled marker');
END//
DELIMITER ;
