"""Test-session setup: always run on synthetic prices.

Real ENTSO-E price files may exist locally (they are git-ignored), so without this the
same tests would behave differently on the author's PC and in CI.
"""
import os

os.environ["SUNDIAL_FORCE_SYNTHETIC"] = "1"
