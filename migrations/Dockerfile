# The project's migrations image: dbmate, by digest (2.36.0), and every
# migration of the project's one database. The box runs it once before
# the services at every start, as the database's migrator
# (docs/migrations/README.md); a release builds it when migrations/
# changes.
FROM ghcr.io/amacneil/dbmate@sha256:520c740c6e0ad73fde2cd1ea7e2b779aaf789d22aca8858f87a478e7094535fb

COPY sql/ /db/migrations/
COPY schema.sql /db/schema.sql

# nobody: it needs no more than to read its files and reach the database
USER 65534

ENV DBMATE_MIGRATIONS_DIR=/db/migrations \
    DBMATE_SCHEMA_FILE=/db/schema.sql \
    DBMATE_NO_DUMP_SCHEMA=true
