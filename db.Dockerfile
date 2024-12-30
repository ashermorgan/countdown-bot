FROM docker.io/postgres:alpine

ADD models/ddl.sql /docker-entrypoint-initdb.d
ADD models/dml-analytics.sql /docker-entrypoint-initdb.d
ADD models/dml-core.sql /docker-entrypoint-initdb.d
ADD models/dml-utils.sql /docker-entrypoint-initdb.d
