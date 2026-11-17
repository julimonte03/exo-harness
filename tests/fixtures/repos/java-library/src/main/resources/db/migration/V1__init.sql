CREATE TABLE books (
    id               BIGSERIAL PRIMARY KEY,
    isbn             VARCHAR(13)  NOT NULL UNIQUE,
    title            VARCHAR(255) NOT NULL,
    author           VARCHAR(255) NOT NULL,
    genre            VARCHAR(20)  NOT NULL,
    total_copies     INTEGER      NOT NULL CHECK (total_copies BETWEEN 1 AND 20),
    available_copies INTEGER      NOT NULL CHECK (available_copies >= 0),
    status           VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE',
    CHECK (available_copies <= total_copies)
);

CREATE TABLE members (
    id        BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email     VARCHAR(255) NOT NULL UNIQUE,
    type      VARCHAR(10)  NOT NULL,
    status    VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE',
    joined_on DATE         NOT NULL
);

CREATE TABLE loans (
    id          BIGSERIAL PRIMARY KEY,
    book_id     BIGINT  NOT NULL REFERENCES books (id),
    member_id   BIGINT  NOT NULL REFERENCES members (id),
    borrowed_on DATE    NOT NULL,
    due_on      DATE    NOT NULL,
    returned_on DATE,
    renewals    INTEGER NOT NULL DEFAULT 0
);
