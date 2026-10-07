-- The project's first migration, and it makes nothing: dbmate needs a
-- file to run, and the box runs dbmate at every start. Tutorial 3's
-- migrations follow it (docs/tutorials/3-the-migration/README.md).
-- py-api's prefix only because every file needs one; it is the
-- database's, not py-api's.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
