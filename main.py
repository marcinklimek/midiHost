#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import argparse
import logging
import sys
import threading
import time

import curses
from pitftgpio import PiTFT_GPIO

try:
    import Queue as queue
except ImportError:  # Python 3
    import queue

from rtmidi.midiutil import open_midiport
from filters import MapControllerValue, MonoPressureToCC, Transpose, MidiFilter, MapChannel, NoteToKaos

pitft = PiTFT_GPIO()
log = logging.getLogger("midifilter")


class MidiDispatcher(threading.Thread):
    def __init__(self, midiin, midiout, *filters):
        super(MidiDispatcher, self).__init__()
        self.midiin = midiin
        self.midiout = midiout
        self.filters = filters
        self._wallclock = time.time()
        self.queue = queue.Queue()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        log.debug("IN: @%0.6f %r", self._wallclock, message)
        self.queue.put((message, self._wallclock))

    def run(self):
        log.debug("Attaching MIDI input callback handler.")
        self.midiin.set_callback(self)

        while True:
            event = self.queue.get()

            if event is None:
                break

            events = [event]

            for filter_ in self.filters:
                events = list(filter_.process(events))

            for event in events:
                log.debug("Out: @%0.6f %r", event[1], event[0])
                self.midiout.send_message(event[0])

    def stop(self):
        self.queue.put(None)






def main(args=None):


    def button3EventHandler(pin):
        screen.addstr(1,0, "-> KAOSS!!!")
        mc.channel = -1
        kaoss.enabled = True
        kaoss.reverse = False if kaoss.reverse else True

        screen.addstr(3,14, "rev: %4s " % (kaoss.reverse,))

    def button4EventHandler(pin):
        screen.addstr(3,24, "scale: %4s " % (kaoss.remap_scale,))
        kaoss.remap_scale = False if kaoss.remap_scale else True


    parser = argparse.ArgumentParser(prog='midifilter', description=__doc__)
    padd = parser.add_argument
    padd('-m', '--mpresstocc', action="store_true",
         help='Map mono pressure (channel aftertouch) to CC')
    padd('-r', '--mapccrange', action="store_true",
         help='Map controller value range to min/max value range')
    padd('-t', '--transpose', action="store_true",
         help='Transpose note on/off event note values')
    padd('-i', '--inport',
         help='MIDI input port number (default: ask)')
    padd('-o', '--outport',
         help='MIDI output port number (default: ask)')
    padd('-v', '--verbose', action="store_true",
         help='verbose output')
    padd('filterargs', nargs="*", type=int,
         help='MIDI filter argument(s)')

    args = parser.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(format="%(name)s: %(levelname)s - %(message)s",
                        level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        midiin, inport_name = open_midiport(args.inport, "input")
        midiout, outport_name = open_midiport(args.outport, "output")
    except IOError as exc:
        print(exc)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 0


    screen = curses.initscr()
    screen.clear()
    #curses.noecho()
    curses.curs_set(0)
    screen.keypad(1)
    #curses.nodelay()

    screen.addstr(0,0, "Main loop")
    screen.addstr(1,0, "-> 0")



    filters = []
    #filters = [CCToBankChange(cc=99, channel=15, msb=0, lsb=1, program=99)]

    mc = MapChannel()
    kaoss = NoteToKaos(screen=screen)
    filters = [mc, kaoss]

    if args.transpose:
        filters.append(Transpose(transpose=args.filterargs[0]))
    if args.mpresstocc:
        filters.append(MonoPressureToCC(cc=args.filterargs[0]))
    if args.mapccrange:
        filters.append(MapControllerValue(*args.filterargs))

    dispatcher = MidiDispatcher(midiin, midiout, *filters)

    pitft.Button3Interrupt(callback = button3EventHandler)
    pitft.Button4Interrupt(callback = button4EventHandler)

    try:
        dispatcher.start()
        while True:

            if pitft.Button1:
                screen.addstr(1,0, "-> 0")
                mc.channel = 0
                kaoss.enabled = False

            if pitft.Button2:
                screen.addstr(1,0, "-> 1")
                mc.channel = 1
                kaoss.enabled = False

            #if pitft.Button3:
            #    screen.addstr(1,0, "-> KAOSS!!!")
            #    mc.channel = -1
            #    kaoss.enabled = True
            #    #kaoss.reverse = False if kaoss.reverse else True

            if kaoss.enabled:
                screen.addstr(5,0, ' '.join(kaoss.sequence) )

            screen.refresh()
            time.sleep(0.1)

    except KeyboardInterrupt:
        dispatcher.stop()
        dispatcher.join()
        print('')

    finally:
        curses.endwin()

        print("Exit.")

        midiin.close_port()
        midiout.close_port()

        del midiin
        del midiout

    return 0


sys.exit(main(sys.argv[1:]) or 0)
