CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 10000),
    summary TEXT NOT NULL CHECK(length(summary) BETWEEN 1 AND 1200),
    tags TEXT NOT NULL CHECK(json_valid(tags) AND json_type(tags) = 'array' AND json_array_length(tags) = 3),
    created_at TEXT NOT NULL
);
