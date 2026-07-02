import pytest

from metadata.generated.schema.type.tableQuery import TableQuery
from metadata.ingestion.lineage.models import Dialect
from metadata.ingestion.processor.query_parser import parse_sql_statement


class TestQueryParser:
    def test_parse_sql_statement_redacts_sql_query(self):
        # Arrange
        sensitive_query = "SELECT * FROM users WHERE email='sensitive@email.com' AND password='secret_password'"

        record = TableQuery(
            query=sensitive_query,
            databaseName="test_db",
            databaseSchema="test_schema",
            serviceName="test_service",
            userName="admin",
        )

        dialect = Dialect.MYSQL

        # Act
        parsed_data = parse_sql_statement(record, dialect)

        # Assert
        assert parsed_data is not None
        # Verify the actual SQL query is completely redacted for Zero Data Leakage
        assert parsed_data.sql == "/* REDACTED FOR ZERO DATA LEAKAGE */"

        # Original query should not be present in the output
        assert "sensitive@email.com" not in parsed_data.sql
        assert "secret_password" not in parsed_data.sql
        assert "SELECT" not in parsed_data.sql
