from unittest.mock import patch


def test_main_invalid_log_level():
    from mnemo_mcp.server import main

    with patch("mnemo_mcp.server.logger") as mock_logger:
        with patch("mnemo_mcp.server.settings") as mock_settings:
            with patch("mnemo_mcp.server.mcp.run"):
                mock_settings.log_level = "INVALID_LEVEL"
                main()

                # Verify that it defaulted to INFO
                mock_logger.add.assert_called_once()
                args, kwargs = mock_logger.add.call_args
                assert kwargs.get("level") == "INFO"


def test_main_valid_log_level():
    from mnemo_mcp.server import main

    with patch("mnemo_mcp.server.logger") as mock_logger:
        with patch("mnemo_mcp.server.settings") as mock_settings:
            with patch("mnemo_mcp.server.mcp.run"):
                mock_settings.log_level = "debug"
                main()

                # Verify that it used DEBUG
                mock_logger.add.assert_called_once()
                args, kwargs = mock_logger.add.call_args
                assert kwargs.get("level") == "DEBUG"
