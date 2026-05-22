from finops_token_saver.domain.authentication import GatewayCredentialValidator


def test_gateway_credential_validator_accepts_valid_bearer_token() -> None:
    validator = GatewayCredentialValidator(("valid-token",))

    assert validator.is_authorized_header("Bearer valid-token") is True


def test_gateway_credential_validator_rejects_invalid_credentials() -> None:
    validator = GatewayCredentialValidator(("valid-token",))

    assert validator.is_authorized_header(None) is False
    assert validator.is_authorized_header("") is False
    assert validator.is_authorized_header("Bearer") is False
    assert validator.is_authorized_header("Bearer ") is False
    assert validator.is_authorized_header("Basic valid-token") is False
    assert validator.is_authorized_header("Bearer wrong-token") is False
