# -*- coding: utf-8 -*-
#
# midifilter/filters.py
#
"""Collection of MIDI filter classes."""

from rtmidi.midiconstants import (BANK_SELECT_LSB, BANK_SELECT_MSB, CHANNEL_PRESSURE,
                                  CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF, PROGRAM_CHANGE, MODULATION_WHEEL)


__all__ = (
    'CCToBankChange',
    'MapControllerValue',
    'MidiFilter',
    'MonoPressureToCC',
    'Transpose',
    'MapChannel',
)


class MidiFilter(object):
    """ABC for midi filters."""

    event_types = ()

    def __init__(self, *args, **kwargs):
        self.args = args
        self.__dict__.update(kwargs)

    def process(self, events):
        """Process incoming events.

        Receives a list of MIDI event tuples (message, timestamp).

        Must return an iterable of event tuples.

        """
        raise NotImplementedError("Abstract method 'process()'.")

    def match(self, msg):
        return msg[0] & 0xF0 in self.event_types


class Transpose(MidiFilter):
    """Transpose note on/off events."""

    event_types = (NOTE_ON, NOTE_OFF)

    def process(self, events):
        for msg, timestamp in events:
            if self.match(msg):
                msg[1] = max(0, min(127, msg[1] + self.transpose)) & 0x7F

            yield msg, timestamp


class MapControllerValue(MidiFilter):
    """Map controller values to min/max range."""

    event_types = (CONTROLLER_CHANGE,)

    def __init__(self, cc, min_, max_, *args, **kwargs):
        super(MapControllerValue, self).__init__(*args, **kwargs)
        self.cc = cc
        self.min = min_
        self.max = max_

    def process(self, events):
        for msg, timestamp in events:
            # check controller number
            if self.match(msg) and msg[1] == self.cc:
                # map controller value
                msg[2] = int(self._map(msg[2]))

            yield msg, timestamp

    def _map(self, value):
        return value * (self.max - self.min) / 127. + self.min


class MonoPressureToCC(MidiFilter):
    """Change mono pressure events into controller change events."""

    event_types = (CHANNEL_PRESSURE,)

    def process(self, events):
        for msg, timestamp in events:
            if self.match(msg):
                channel = msg[0] & 0xF
                msg = [CONTROLLER_CHANGE | channel, self.cc, msg[1]]

            yield msg, timestamp


class CCToBankChange(MidiFilter):
    """Map controller change to a bank select, program change sequence."""

    event_types = (CONTROLLER_CHANGE,)

    def process(self, events):
        for msg, timestamp in events:
            channel = msg[0] & 0xF

            # check controller number & channel
            if (self.match(msg) and channel == self.channel and
                    msg[1] == self.cc):
                msb = [CONTROLLER_CHANGE + channel, BANK_SELECT_MSB, self.msb]
                lsb = [CONTROLLER_CHANGE + channel, BANK_SELECT_LSB, self.lsb]
                pc = [PROGRAM_CHANGE + channel, self.program]
                yield msb, timestamp
                yield lsb, timestamp
                yield pc, timestamp
            else:
                yield msg, timestamp


class MapChannel(MidiFilter):

    event_types = (NOTE_ON, NOTE_OFF)
    channel = 0

    def process(self, events):

        for msg, timestamp in events:

            if self.channel == -1:
                yield msg, timestamp

            elif self.match(msg):
                msg[0] = (msg[0] & 0xf0) | self.channel

                yield msg, timestamp


KAOSS_CC_PAD  =    92           # pad on/off control change # (check the manual for more information)
KAOSS_CC_X    =    12           # pad on/off control change # (check the manual for more information)
KAOSS_CC_Y    =    13           # pad on/off control change # (check the manual for more information)
AKAI_MK_MINI_KNOB_A1 = 48

class NoteToKaos(MidiFilter):
    """Change notes  events into Kaossilator Pro change events."""

    event_types = (NOTE_ON, NOTE_OFF, CONTROLLER_CHANGE)
    remap_scale = False
    reverse = True
    enabled = False
    key_counter = 0
    yPad = 64
    xPad = 64

    notes = ("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")

    sequence = ["    ", "    ", "    ", "    ", "    ", "    ", "    ", "    "]
    sequence_idx = 0


    def add_note(self, note):
        n = self.notes[note%12]

        pad = ''
        if len(n)>1:
            pad = ' '

        self.sequence[ self.sequence_idx  ] =  "%s%-2s%s" %(n, int(note/12),pad)
        self.sequence_idx = (self.sequence_idx + 1 ) % len(self.sequence)

    def remap(self, x, oMin, oMax, nMin, nMax ):

        #range check
        if oMin == oMax:
            #print "Warning: Zero input range"
            return None

        if nMin == nMax:
            #print "Warning: Zero output range"
            return None

        #check reversed input range
        reverseInput = False
        oldMin = min( oMin, oMax )
        oldMax = max( oMin, oMax )
        if not oldMin == oMin:
            reverseInput = True

        #check reversed output range
        reverseOutput = False
        newMin = min( nMin, nMax )
        newMax = max( nMin, nMax )
        if not newMin == nMin :
            reverseOutput = True

        portion = (x-oldMin)*(newMax-newMin)/(oldMax-oldMin)
        if reverseInput:
            portion = (oldMax-x)*(newMax-newMin)/(oldMax-oldMin)

        result = portion + newMin
        if reverseOutput:
            result = newMax - portion

        return int(result)

    def process(self, events):
        for msg, timestamp in events:

            if self.match(msg) and self.enabled:
                channel = msg[0] & 0xF

                #yPad = msg[2] # velocity

                self.screen.addstr(3,0, "n:%4s v:%4s rev:%4s " % (self.xPad, self.yPad, self.reverse))

                if msg[0] & 0xF0 == NOTE_OFF:

                    self.key_counter -= 1
                    if self.key_counter == 0:
                        msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_PAD, 0]
                        yield msg, timestamp

                elif msg[0] & 0xF0 == NOTE_ON:
                    self.key_counter += 1

                    if self.reverse:
                        self.yPad = self.remap(msg[1], 48, 72, 0, 127)
                    else:
                        self.xPad = msg[1] # note

                    if self.remap_scale:
                        self.xPad = self.remap(msg[1], 48, 72, 0, 127)


                    self.add_note( self.xPad )

                    msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_X, self.xPad]
                    yield msg, timestamp

                    msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_Y, self.yPad]
                    yield msg, timestamp

                    msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_PAD, 127]
                    yield msg, timestamp


                elif msg[0] & 0xF0 == CONTROLLER_CHANGE:

                    if msg[1] == AKAI_MK_MINI_KNOB_A1:

                        self.screen.addstr(4,0, "c:%4s v:%4s " % (msg[1], msg[2]))

                        if self.reverse:
                            self.xPad = msg[2]

                            if self.remap_scale:
                                self.xPad = self.remap(msg[1], 48, 72, 0, 127)

                            msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_X, self.xPad]
                            yield msg, timestamp

                            msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_Y, self.yPad]
                            yield msg, timestamp

                            msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_PAD, 127]
                            yield msg, timestamp

                        else:
                            self.yPad = msg[2]
                            if self.key_counter > 0:
                                msg = [CONTROLLER_CHANGE | channel, KAOSS_CC_Y, self.yPad]
                                yield msg, timestamp

            else:
                if not self.enabled:
                    self.screen.addstr(3,0, "DISABLED     " )

                yield msg, timestamp
