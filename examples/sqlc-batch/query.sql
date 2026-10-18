-- name: InsertItem :batchexec
INSERT INTO sqlc_batch_items (id, note) VALUES ($1, $2);
