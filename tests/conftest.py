"""When Hermes is not installed, give the plugin a stand-in for agent.secret_scope.

The stand-in reads the process environment, which is what Hermes does for a single profile.
Tests that check multi-profile behaviour skip when the stand-in is in use.
"""
import os
import sys
import types

try:
    import agent.secret_scope  # noqa: F401
except ImportError:
    agent = types.ModuleType("agent")
    secret_scope = types.ModuleType("agent.secret_scope")

    class UnscopedSecretError(RuntimeError):
        pass

    def get_secret(name, default=None):
        return os.environ.get(name, default)

    secret_scope.UnscopedSecretError = UnscopedSecretError
    secret_scope.get_secret = get_secret
    secret_scope.IS_TEST_STAND_IN = True
    agent.secret_scope = secret_scope
    sys.modules["agent"] = agent
    sys.modules["agent.secret_scope"] = secret_scope
