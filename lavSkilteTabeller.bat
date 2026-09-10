set psql="c:\Program Files\PostgreSQL\14\bin\psql"
%psql% -U postgres -p 5432 -h localhost -d %1 -f skilteplan.sql