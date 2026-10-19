"""Incremental eight-channel averaging, one fresh ADC reading per step."""


class ADCAverage:
    def __init__(self, samples=1):
        if samples not in (1, 2, 4, 8, 16, 32):
            raise ValueError("unsupported sample count")
        self.samples = samples
        self.sums = [0.0] * 8
        self.channel = 0
        self.rounds = 0

    def step(self, adc):
        # read_channel synchronizes a new conversion; no repeated cached samples.
        self.sums[self.channel] += adc.read_channel(self.channel)
        self.channel += 1
        if self.channel == 8:
            self.channel = 0
            self.rounds += 1
            if self.rounds == self.samples:
                result = [value / self.samples for value in self.sums]
                self.sums = [0.0] * 8
                self.rounds = 0
                return result
        return None
