# coding: utf-8

from howl_editor.ps1 import spu


class SampleRateConverter:
    """Turns a sample rate into the SPU pitch register that plays it."""

    def pitch_for_rate(self, rate_hz: float) -> int:
        """The pitch register that plays a sample recorded at `rate_hz` at its
        own speed."""
        return round(rate_hz / spu.SAMPLE_RATE * spu.FREQUENCY_UNIT)
