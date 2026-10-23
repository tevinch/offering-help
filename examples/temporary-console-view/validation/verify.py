#!/usr/bin/env python3
"""Observe the real app through a POSIX PTY and a headless xterm terminal."""
import argparse
import codecs
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import termios
import time


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Session:
    def __init__(self, dotnet, assembly, cols, rows, term='xterm-256color'):
        self.raw = bytearray()
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.terminal = subprocess.Popen(['node', str(Path(__file__).with_name('terminal.cjs')), str(cols), str(rows)],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = os.environ.copy()
            for key in ['NO_COLOR', 'FORCE_COLOR', 'CLICOLOR_FORCE', 'CI', 'GITHUB_ACTIONS', 'TEAMCITY_VERSION']:
                env.pop(key, None)
            env['TERM'] = term
            os.execvpe(dotnet, [dotnet, str(assembly)], env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        self.state = self.feed('')
        self.status = None

    def feed(self, text):
        self.terminal.stdin.write(json.dumps({'text': text}) + '\n')
        self.terminal.stdin.flush()
        require(select.select([self.terminal.stdout], [], [], 5)[0], 'Terminal emulator response timed out')
        result = json.loads(self.terminal.stdout.readline())
        if result['replies']:
            os.write(self.fd, result['replies'].encode())
        return result

    def pump(self, timeout=0.1):
        if select.select([self.fd], [], [], timeout)[0]:
            try:
                chunk = os.read(self.fd, 65536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                chunk = b''
            if chunk:
                self.raw.extend(chunk)
                self.state = self.feed(self.decoder.decode(chunk))
        if self.status is None:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.status = os.waitstatus_to_exitcode(status)

    def wait(self, predicate, label):
        end = time.monotonic() + 12
        while time.monotonic() < end:
            if predicate(self.state):
                return self.state
            self.pump()
            if self.status is not None:
                # Drain final PTY bytes before deciding the visible result.
                self.pump(0)
                if predicate(self.state):
                    return self.state
                break
        raise AssertionError(f'{label}: exit={self.status}, screen={self.state}')

    def send(self, value):
        os.write(self.fd, value)

    def close(self):
        if self.status is None:
            try:
                os.killpg(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.waitpid(self.pid, 0)
        os.close(self.fd)
        self.terminal.terminate()
        self.terminal.wait(timeout=5)


def text(state):
    return '\n'.join(state['active'])


def check_roundtrip(dotnet, assembly, cols, rows):
    session = Session(dotnet, assembly, cols, rows)
    snapshots = []
    try:
        first = session.wait(lambda s: 'Enter opens view 1.' in text(s), 'initial main content')
        require(first['type'] == 'normal' and 'Existing report: 42 items.' in text(first), 'Initial main content missing')
        previous = first['normal'][:]
        for number, choice, arrows in [(1, 'Beta', 1), (2, 'Gamma', 2)]:
            session.send(b'\r')
            visible = session.wait(lambda s: all(value in text(s) for value in ['Context widget', 'Summary widget',
                                   'Choose a destination', 'Alpha', 'Beta', 'Gamma']), 'simultaneous widgets and choices')
            require(visible['type'] == 'alternate', 'Temporary view must occupy alternate screen, preserving main content')
            require(visible['normal'] == previous, 'Normal screen changed while temporary view was open')
            snapshots.append({'phase': f'view{number}', **visible})
            session.send(b'\x1b[B' * arrows + b'\r')
            restored = session.wait(lambda s: f'Returned {number}: {choice}' in text(s), 'actual selected result')
            require(restored['type'] == 'normal', 'Main screen was not restored')
            require('Existing report: 42 items.' in text(restored), 'Existing content was removed')
            require(not any(value in text(restored) for value in ['Context widget', 'Summary widget', 'Choose a destination']),
                    'Temporary widgets or prompt remained on main screen')
            if number == 2:
                require('Returned 1: Beta' in text(restored), 'Previous result was lost on repeated view')
            snapshots.append({'phase': f'restored{number}', **restored})
            if number == 1:
                session.wait(lambda s: 'Enter opens view 2.' in text(s), 'second interaction invitation')
                previous = session.state['normal'][:]
        session.wait(lambda s: 'Finished both selections.' in text(s), 'finished selections')
        end = time.monotonic() + 5
        while session.status is None and time.monotonic() < end:
            session.pump()
        require(session.status == 0, f'App exit={session.status}')
        return {'cols': cols, 'rows': rows, 'snapshots': snapshots, 'exit': session.status}
    finally:
        session.close()


def check_skip(dotnet, assembly, cols, rows, term):
    session = Session(dotnet, assembly, cols, rows, term)
    try:
        session.wait(lambda s: 'View unavailable:' in text(s), 'capability/size refusal')
        end = time.monotonic() + 5
        while session.status is None and time.monotonic() < end:
            session.pump()
        require(session.status == 2, 'Unsupported view must have nonzero exit')
        require(session.state['type'] == 'normal' and 'Existing report: 42 items.' in text(session.state), 'Skip removed original content')
        require(b'\x1b[?1049h' not in session.raw and b'\x1b[2J' not in session.raw, 'Skip entered or cleared a screen')
        require('Choose a destination' not in text(session.state), 'Unsupported terminal was prompted')
        return {'cols': cols, 'rows': rows, 'term': term, 'exit': session.status, 'screen': session.state}
    finally:
        session.close()


def check_redirected(dotnet, assembly, mode):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
    env = dict(os.environ, TERM='xterm-256color')
    try:
        if mode == 'input':
            result = subprocess.run([dotnet, str(assembly)], input='', stdout=slave, stderr=subprocess.PIPE,
                                    env=env, text=True, timeout=10)
            chunks = []
            while select.select([master], [], [], 0.2)[0]:
                try:
                    value = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                if not value:
                    break
                chunks.append(value)
            output = b''.join(chunks).decode('utf-8')
        elif mode == 'output':
            result = subprocess.run([dotnet, str(assembly)], stdin=slave, capture_output=True,
                                    env=env, text=True, timeout=10)
            output = result.stdout
        else:
            result = subprocess.run([dotnet, str(assembly)], input='', capture_output=True,
                                    env=env, text=True, timeout=10)
            output = result.stdout
        require(result.returncode == 2 and 'View unavailable:' in output, f'Redirected {mode} must skip without blocking')
        require('Existing report: 42 items.' in output, f'Redirected {mode} removed original output')
        require('\x1b[?1049h' not in output and '\x1b[2J' not in output, f'Redirected {mode} entered or cleared a screen')
        if mode != 'input':
            require('\x1b[' not in output, f'Redirected {mode} output contains ANSI sequences')
        require('Choose a destination' not in output, f'Redirected {mode} was prompted')
        return {'mode': mode, 'exit': result.returncode, 'stdout': output}
    finally:
        if slave is not None:
            os.close(slave)
        os.close(master)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--roundtrip-only', action='store_true')
    args = parser.parse_args()
    dotnet = os.environ.get('DOTNET', 'dotnet')
    results = {'roundtrips': [check_roundtrip(dotnet, args.assembly.resolve(), 80, 24),
                              check_roundtrip(dotnet, args.assembly.resolve(), 60, 18)]}
    if not args.roundtrip_only:
        results['skips'] = [check_skip(dotnet, args.assembly.resolve(), 59, 18, 'xterm-256color'),
                            check_skip(dotnet, args.assembly.resolve(), 60, 17, 'xterm-256color'),
                            check_skip(dotnet, args.assembly.resolve(), 80, 24, 'dumb')]
        results['redirected'] = [check_redirected(dotnet, args.assembly.resolve(), mode) for mode in ['input', 'output', 'both']]
    if args.output:
        args.output.write_text(json.dumps(results, indent=2) + '\n')
    print('PASS: real selections, simultaneous widgets, restored main content, repeat and supported guards.')
