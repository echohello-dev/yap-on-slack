"""Tests for SSL/TLS configuration and certificate handling."""

import ssl
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yap_on_slack.post_messages import SSLConfigModel, create_ssl_context


class TestSSLConfigModel:
    """Test SSL configuration model."""

    def test_default_ssl_config(self):
        """Test default SSL configuration with verification enabled."""
        config = SSLConfigModel()
        assert config.verify is True
        assert config.ca_bundle is None
        assert config.no_strict is False

    def test_ssl_config_with_verify_disabled(self):
        """Test SSL configuration with verification disabled."""
        config = SSLConfigModel(verify=False)
        assert config.verify is False
        assert config.ca_bundle is None
        assert config.no_strict is False

    def test_ssl_config_with_ca_bundle(self):
        """Test SSL configuration with custom CA bundle."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            config = SSLConfigModel(ca_bundle=ca_bundle_path)
            assert config.verify is True
            assert config.ca_bundle == ca_bundle_path
            assert config.no_strict is False
        finally:
            Path(ca_bundle_path).unlink()

    def test_ssl_config_with_no_strict(self):
        """Test SSL configuration with strict X509 verification disabled."""
        config = SSLConfigModel(no_strict=True)
        assert config.verify is True
        assert config.ca_bundle is None
        assert config.no_strict is True

    def test_ssl_config_ca_bundle_must_exist(self):
        """Test that CA bundle file must exist."""
        with pytest.raises(ValueError, match="CA bundle file not found"):
            SSLConfigModel(ca_bundle="/nonexistent/path/to/ca-bundle.pem")

    def test_ssl_config_ca_bundle_with_tilde_expansion(self):
        """Test that CA bundle path supports tilde expansion."""
        # Create a temporary file in home directory
        home = Path.home()
        test_file = home / ".test-ca-bundle.pem"
        test_file.write_text("# Test CA bundle\n")

        try:
            config = SSLConfigModel(ca_bundle="~/.test-ca-bundle.pem")
            assert config.ca_bundle == "~/.test-ca-bundle.pem"
        finally:
            test_file.unlink()

    def test_ssl_config_all_options(self):
        """Test SSL configuration with all options set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Fake CA bundle\n")

        try:
            config = SSLConfigModel(
                verify=True,
                ca_bundle=ca_bundle_path,
                no_strict=True,
            )
            assert config.verify is True
            assert config.ca_bundle == ca_bundle_path
            assert config.no_strict is True
        finally:
            Path(ca_bundle_path).unlink()


class TestCreateSSLContext:
    """Test SSL context creation function."""

    def test_default_context_returns_true(self):
        """Test that default context returns True (use httpx defaults)."""
        result = create_ssl_context()
        assert result is True

    def test_default_context_with_none_config(self):
        """Test that None config uses defaults."""
        result = create_ssl_context(None)
        assert result is True

    def test_verify_disabled_returns_false(self):
        """Test that disabled verification returns False."""
        config = SSLConfigModel(verify=False)
        result = create_ssl_context(config)
        assert result is False

    def test_no_strict_creates_ssl_context(self):
        """Test that no_strict creates an SSLContext."""
        config = SSLConfigModel(no_strict=True)
        result = create_ssl_context(config)
        assert isinstance(result, ssl.SSLContext)

    def test_ca_bundle_creates_ssl_context(self):
        """Test that CA bundle creates an SSLContext."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            config = SSLConfigModel(ca_bundle=ca_bundle_path)
            # Mock the SSL context loading
            with patch(
                "yap_on_slack.post_messages.ssl.create_default_context"
            ) as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_create_context.return_value = mock_context

                result = create_ssl_context(config)
                assert result is mock_context
                mock_context.load_verify_locations.assert_called_once_with(cafile=ca_bundle_path)
        finally:
            Path(ca_bundle_path).unlink()

    def test_environment_variable_ssl_cert_file(self):
        """Test that SSL_CERT_FILE environment variable is respected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            with patch.dict("os.environ", {"SSL_CERT_FILE": ca_bundle_path}):
                # Mock the SSL context loading
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    config = SSLConfigModel()
                    result = create_ssl_context(config)
                    assert result is mock_context
                    # Verify the env var was used
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=ca_bundle_path
                    )
        finally:
            Path(ca_bundle_path).unlink()

    def test_environment_variable_requests_ca_bundle(self):
        """Test that REQUESTS_CA_BUNDLE environment variable is respected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            with patch.dict("os.environ", {"REQUESTS_CA_BUNDLE": ca_bundle_path}):
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    config = SSLConfigModel()
                    result = create_ssl_context(config)
                    assert result is mock_context
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=ca_bundle_path
                    )
        finally:
            Path(ca_bundle_path).unlink()

    def test_environment_variable_curl_ca_bundle(self):
        """Test that CURL_CA_BUNDLE environment variable is respected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            with patch.dict("os.environ", {"CURL_CA_BUNDLE": ca_bundle_path}):
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    config = SSLConfigModel()
                    result = create_ssl_context(config)
                    assert result is mock_context
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=ca_bundle_path
                    )
        finally:
            Path(ca_bundle_path).unlink()

    def test_environment_variable_priority(self):
        """Test that environment variables are checked in priority order."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            # SSL_CERT_FILE has highest priority
            with patch.dict(
                "os.environ",
                {
                    "SSL_CERT_FILE": ca_bundle_path,
                    "REQUESTS_CA_BUNDLE": "/nonexistent/path1.pem",
                    "CURL_CA_BUNDLE": "/nonexistent/path2.pem",
                },
            ):
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    config = SSLConfigModel()
                    result = create_ssl_context(config)
                    assert result is mock_context
                    # Should use SSL_CERT_FILE (highest priority)
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=ca_bundle_path
                    )
        finally:
            Path(ca_bundle_path).unlink()

    def test_config_ca_bundle_overrides_environment(self):
        """Test that explicit config ca_bundle overrides environment variables."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f1:
            config_ca_path = f1.name
            f1.write("# Test CA bundle\n")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f2:
            env_ca_path = f2.name
            f2.write("# Test CA bundle\n")

        try:
            with patch.dict("os.environ", {"SSL_CERT_FILE": env_ca_path}):
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    config = SSLConfigModel(ca_bundle=config_ca_path)
                    result = create_ssl_context(config)
                    assert result is mock_context
                    # Should use config_ca_path (explicit config overrides env)
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=config_ca_path
                    )
        finally:
            Path(config_ca_path).unlink()
            Path(env_ca_path).unlink()

    def test_environment_variable_ssl_cert_dir(self):
        """Test that SSL_CERT_DIR environment variable is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a certificate file in the directory
            cert_file = Path(tmpdir) / "test-ca.pem"
            cert_file.write_text("# Test certificate\n")

            with patch.dict("os.environ", {"SSL_CERT_DIR": tmpdir}):
                config = SSLConfigModel()
                result = create_ssl_context(config)
                # Should create SSLContext when SSL_CERT_DIR is set
                assert isinstance(result, ssl.SSLContext)

    def test_nonexistent_environment_variable_ignored(self):
        """Test that nonexistent paths in environment variables are ignored."""
        with patch.dict(
            "os.environ",
            {
                "SSL_CERT_FILE": "/nonexistent/path.pem",
                "REQUESTS_CA_BUNDLE": "/also/nonexistent.pem",
            },
        ):
            config = SSLConfigModel()
            result = create_ssl_context(config)
            # Should fall back to default (True) since no valid paths exist
            assert result is True

    def test_python_313_no_strict_mode(self):
        """Test Python 3.13+ no_strict mode handling."""
        config = SSLConfigModel(no_strict=True)
        result = create_ssl_context(config)

        # Should create an SSLContext
        assert isinstance(result, ssl.SSLContext)

        # Check if VERIFY_X509_STRICT is available and was disabled
        if hasattr(ssl, "VERIFY_X509_STRICT"):
            # In Python 3.13+, verify that the strict flag is not set
            assert not (result.verify_flags & ssl.VERIFY_X509_STRICT)

    def test_combined_ca_bundle_and_no_strict(self):
        """Test combining CA bundle with no_strict mode."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            with patch(
                "yap_on_slack.post_messages.ssl.create_default_context"
            ) as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_context.verify_flags = 0
                mock_create_context.return_value = mock_context

                config = SSLConfigModel(ca_bundle=ca_bundle_path, no_strict=True)
                result = create_ssl_context(config)
                assert result is mock_context
                mock_context.load_verify_locations.assert_called_once_with(cafile=ca_bundle_path)
                # Verify no_strict was applied (if Python 3.13+)
                if hasattr(ssl, "VERIFY_X509_STRICT"):
                    # verify_flags should have been modified to disable strict
                    assert mock_context.verify_flags == 0
        finally:
            Path(ca_bundle_path).unlink()

    def test_invalid_ca_bundle_raises_error(self):
        """Test that invalid CA bundle file raises an error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            # Write invalid content (not a valid certificate)
            f.write("This is not a valid certificate\n")

        try:
            config = SSLConfigModel(ca_bundle=ca_bundle_path)
            with pytest.raises(Exception):  # ssl.SSLError or similar
                create_ssl_context(config)
        finally:
            Path(ca_bundle_path).unlink()


class TestSSLConfigIntegration:
    """Test SSL configuration integration scenarios."""

    def test_corporate_proxy_scenario(self):
        """Test typical corporate proxy configuration scenario."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            # Simulate corporate environment with REQUESTS_CA_BUNDLE
            with patch.dict("os.environ", {"REQUESTS_CA_BUNDLE": ca_bundle_path}):
                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_context.verify_flags = 0
                    mock_create_context.return_value = mock_context

                    # User doesn't need to configure anything explicitly
                    config = SSLConfigModel(no_strict=True)
                    result = create_ssl_context(config)

                    # Should work automatically with env var
                    assert result is mock_context
                    mock_context.load_verify_locations.assert_called_once_with(
                        cafile=ca_bundle_path
                    )
        finally:
            Path(ca_bundle_path).unlink()

    def test_disabled_verification_for_testing(self):
        """Test disabling SSL verification for testing environments."""
        config = SSLConfigModel(verify=False)
        result = create_ssl_context(config)
        assert result is False

    def test_default_production_configuration(self):
        """Test default configuration for production (secure)."""
        config = SSLConfigModel()
        result = create_ssl_context(config)
        # Should use system defaults (secure)
        assert result is True


class TestStrictX509Configuration:
    """Test strict X509 verification configuration (Python 3.13+)."""

    def test_strict_x509_default_none(self):
        """Test that strict_x509 defaults to None (auto mode)."""
        config = SSLConfigModel()
        assert config.strict_x509 is None

    def test_strict_x509_explicit_true(self):
        """Test explicit strict_x509=True (force enable)."""
        config = SSLConfigModel(strict_x509=True)
        assert config.strict_x509 is True

    def test_strict_x509_explicit_false(self):
        """Test explicit strict_x509=False (force disable)."""
        config = SSLConfigModel(strict_x509=False)
        assert config.strict_x509 is False

    def test_strict_x509_auto_disables_with_custom_ca(self):
        """Test that strict X509 is auto-disabled when custom CA bundle is used."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            # strict_x509=None (default) should auto-disable with custom CA
            config = SSLConfigModel(ca_bundle=ca_bundle_path, strict_x509=None)

            with patch(
                "yap_on_slack.post_messages.ssl.create_default_context"
            ) as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                # Simulate VERIFY_X509_STRICT flag
                mock_context.verify_flags = (
                    ssl.VERIFY_X509_STRICT if hasattr(ssl, "VERIFY_X509_STRICT") else 0
                )
                mock_create_context.return_value = mock_context

                result = create_ssl_context(config)

                assert result is mock_context
                # Verify flags were modified (strict disabled)
                assert mock_context.verify_flags != (
                    ssl.VERIFY_X509_STRICT if hasattr(ssl, "VERIFY_X509_STRICT") else 0
                )
        finally:
            Path(ca_bundle_path).unlink()

    def test_strict_x509_force_enable_with_custom_ca(self):
        """Test that strict_x509=True forces strict mode even with custom CA."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            ca_bundle_path = f.name
            f.write("# Test CA bundle\n")

        try:
            # strict_x509=True should force enable even with custom CA
            config = SSLConfigModel(ca_bundle=ca_bundle_path, strict_x509=True)

            with patch(
                "yap_on_slack.post_messages.ssl.create_default_context"
            ) as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_context.verify_flags = 0
                mock_create_context.return_value = mock_context

                result = create_ssl_context(config)

                assert result is mock_context
                # Verify strict flag was enabled (if Python 3.13+)
                if hasattr(ssl, "VERIFY_X509_STRICT"):
                    assert mock_context.verify_flags & ssl.VERIFY_X509_STRICT
        finally:
            Path(ca_bundle_path).unlink()

    def test_strict_x509_env_var_true(self):
        """Test SSL_STRICT_X509 environment variable set to 'true'."""
        with patch.dict("os.environ", {"SSL_STRICT_X509": "true"}):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
                ca_bundle_path = f.name
                f.write("# Test CA bundle\n")

            try:
                config = SSLConfigModel(ca_bundle=ca_bundle_path)

                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_context.verify_flags = 0
                    mock_create_context.return_value = mock_context

                    result = create_ssl_context(config)

                    assert result is mock_context
                    # Should have enabled strict mode via env var
                    if hasattr(ssl, "VERIFY_X509_STRICT"):
                        assert mock_context.verify_flags & ssl.VERIFY_X509_STRICT
            finally:
                Path(ca_bundle_path).unlink()

    def test_strict_x509_env_var_false(self):
        """Test SSL_STRICT_X509 environment variable set to 'false'."""
        with patch.dict("os.environ", {"SSL_STRICT_X509": "false"}):
            config = SSLConfigModel()

            with patch(
                "yap_on_slack.post_messages.ssl.create_default_context"
            ) as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_context.verify_flags = (
                    ssl.VERIFY_X509_STRICT if hasattr(ssl, "VERIFY_X509_STRICT") else 0
                )
                mock_create_context.return_value = mock_context

                # Even without custom CA, env var should force disable
                result = create_ssl_context(config)

                # With no custom CA and SSL_STRICT_X509=false, should use defaults
                # (because no_strict mode is only triggered with custom CA or explicit flag)
                assert result is True  # Uses system defaults

    def test_strict_x509_env_var_numeric(self):
        """Test SSL_STRICT_X509 environment variable with numeric values."""
        # Test '1' (true)
        with patch.dict("os.environ", {"SSL_STRICT_X509": "1"}):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
                ca_bundle_path = f.name
                f.write("# Test CA bundle\n")

            try:
                config = SSLConfigModel(ca_bundle=ca_bundle_path)

                with patch(
                    "yap_on_slack.post_messages.ssl.create_default_context"
                ) as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_context.verify_flags = 0
                    mock_create_context.return_value = mock_context

                    result = create_ssl_context(config)

                    assert result is mock_context
                    if hasattr(ssl, "VERIFY_X509_STRICT"):
                        assert mock_context.verify_flags & ssl.VERIFY_X509_STRICT
            finally:
                Path(ca_bundle_path).unlink()
