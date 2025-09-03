from __future__ import annotations
import logging
from typing import Dict, Callable, List, Tuple, Any

from pforge.recovery.detectors import (
    packages, runtime_versions, services, ports, time_tz
)
from pforge.recovery.actions import (
    pkg_resolve, service_boot, port_reassign, tz_set
)

logger = logging.getLogger(__name__)

# A check is a function that returns a boolean (is_ok) and a details dict.
CheckFunction = Callable[..., Tuple[bool, Dict[str, Any]]]
# An action is a function that returns a proof dictionary.
ActionFunction = Callable[..., Dict[str, Any]]

class PreflightEngine:
    """
    Orchestrates preflight checks and remediation actions.
    """
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.checks: List[Tuple[str, CheckFunction, Dict]] = []
        self.remediations: Dict[str, ActionFunction] = {}
        self._register_checks_and_actions()

    def _register_checks_and_actions(self):
        """
        Registers all available checks and their corresponding remediations.
        In a real system, this might be done via dynamic discovery or a
        more formal registration mechanism.
        """
        # Simple checks first
        self.add_check("python_version", runtime_versions.check_python_version)
        self.add_check("timezone", time_tz.check_timezone, remediation=tz_set.set_timezone_to_utc)

        # Package checks
        self.add_check("pip_dependencies", packages.check_pip_dependencies, remediation=pkg_resolve.install_packages)
        # Assuming npm check needs the repo root from config
        if "repo_root" in self.config:
            self.add_check("npm_dependencies", packages.check_npm_dependencies,
                           args={"repo_root": self.config["repo_root"]})

        # Service / Port checks
        self.add_check("redis_availability", services.check_redis_availability,
                       remediation=service_boot.start_fake_redis)
        # Example of a check that might need a remediation to find a new port
        if "service_port" in self.config:
            self.add_check("port_collision", ports.check_port_collision,
                           args={"port": self.config["service_port"]},
                           remediation=port_reassign.find_free_port)

    def add_check(
        self,
        name: str,
        check_func: CheckFunction,
        args: Dict | None = None,
        remediation: ActionFunction | None = None
    ):
        """Adds a check and its optional remediation action."""
        self.checks.append((name, check_func, args or {}))
        if remediation:
            self.remediations[name] = remediation

    def run(self, max_retries: int = 3) -> Tuple[bool, List[Dict]]:
        """
        Runs all registered checks, attempting remediation on failure.

        The process is repeated up to `max_retries` times to allow for
        remediations to take effect and be verified.

        Returns:
            A tuple containing an overall success flag and a list of log entries
            for each check and action performed.
        """
        log: List[Dict] = []
        for i in range(max_retries):
            all_ok = True
            failed_checks = []

            for name, check_func, kwargs in self.checks:
                is_ok, witness = check_func(**kwargs)
                log.append({"type": "check", "name": name, "is_ok": is_ok, "witness": witness})
                if not is_ok:
                    all_ok = False
                    failed_checks.append(name)

            if all_ok:
                logger.info(f"All preflight checks passed on attempt {i+1}.")
                return True, log

            logger.warning(f"Attempt {i+1}: Failed checks: {failed_checks}")

            # Attempt remediation for the first failed check that has one.
            remediated = False
            for name in failed_checks:
                if name in self.remediations:
                    action_func = self.remediations[name]
                    logger.info(f"Attempting remediation for '{name}' with action '{action_func.__name__}'...")
                    proof = action_func()
                    log.append({"type": "action", "name": action_func.__name__, "proof": proof})
                    # We remediated one, now we should break and retry all checks.
                    remediated = True
                    break

            if not remediated:
                logger.error("Preflight checks failed and no further remediation could be attempted.")
                return False, log

        logger.error(f"Preflight checks failed after {max_retries} attempts.")
        return False, log
