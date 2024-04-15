#!/usr/bin/env python3

import errno
import locale
import os
import pty
import re
import subprocess
import sys
from typing import Iterator, List, Optional, Tuple  # noqa: F401  # pylint: disable=unused-import

__author__ = "Ingo Meyer"
__email__ = "IJ_M@gmx.de"
__license__ = "MIT"
__version_info__ = (0, 3, 0)
__version__ = ".".join(map(str, __version_info__))

BLOCK_SIZE = 1024
COMMIT_CHAR_ASCII = "*"
COMMIT_CHAR_UNICODE = "●"


class ProcessError(Exception):
    def __init__(self, returncode: int) -> None:
        super().__init__()
        self.returncode = returncode


class GitLogError(ProcessError):
    pass


class PagerError(ProcessError):
    pass


def get_locale_encoding() -> str:
    encoding = locale.getlocale()[1]
    if encoding is None:
        encoding = "ascii"
    return encoding


def is_locale_utf8() -> bool:
    locale_encoding = get_locale_encoding()
    return locale_encoding.lower() == "utf-8"


def decode(byte_string: bytes) -> str:
    encoding = get_locale_encoding()
    return byte_string.decode(encoding, "replace")


def encode(unicode_string: str) -> bytes:
    encoding = get_locale_encoding()
    return unicode_string.encode(encoding, "replace")


def get_pager_with_options() -> List[str]:
    pager = None  # type: Optional[str]
    pager_options = []  # type: List[str]
    try:
        pager = subprocess.check_output(["git", "config", "--get", "core.pager"], universal_newlines=True)
    except subprocess.CalledProcessError:
        pass
    if not pager:
        for env_variable in ("GITPAGER", "PAGER"):
            if env_variable in os.environ:
                pager = os.environ[env_variable]
                if pager:
                    break
        else:
            pager = "less"
    if pager in ("less", "more"):
        pager_options = ["-R"]
    return [pager] + pager_options


def gen_git_log() -> Iterator[str]:
    master_fd, slave_fd = pty.openpty()
    git_log_process = subprocess.Popen(
        ["git", "--no-pager", "log", "--color=always", "--all", "--graph", "--format=%C(auto)%h%d %s %G?"],
        stdout=slave_fd,
    )
    os.close(slave_fd)  # otherwise read from `master_fd` will wait forever
    byte_block = b""
    try:
        while True:
            try:
                current_bytes = os.read(master_fd, BLOCK_SIZE)
            except OSError as e:
                if e.errno != errno.EIO:
                    raise
                break  # EIO means EOF on some systems
            if not current_bytes:
                break
            byte_block += current_bytes
            if current_bytes.find(b"\n") >= 0:
                lines = byte_block.split(b"\n")
                for line in lines[:-1]:
                    yield decode(line)
                byte_block = lines[-1]
    finally:
        os.close(master_fd)
    if byte_block:
        yield decode(byte_block)
    returncode = git_log_process.wait()
    if returncode != 0:
        raise GitLogError(returncode)


def gen_colorized_git_log_output(git_log_iterator: Iterator[str]) -> Iterator[str]:
    def colorize_sign_state(sign_state: str) -> str:
        sign_to_escape_code = {
            "G": "\x1b[32m",
            "B": "\x1b[31m",
            "U": "\x1b[33m",
            "X": "\x1b[31m",
            "Y": "\x1b[31m",
            "R": "\x1b[31m",
            "E": "\x1b[33m",
            "N": "",
        }
        sign_to_text = {
            "G": "✓",
            "B": "✗ (bad)",
            "U": "? (unknown validity)",
            "X": "✗ (expired)",
            "Y": "✗ (expired key)",
            "R": "✗ (revoked key)",
            "E": "? (missing key)",
            "N": "",
        }
        if sign_to_text.get(sign_state) == "":
            return ""
        escape_code = sign_to_escape_code.get(sign_state, "")
        sign_text = sign_to_text.get(sign_state)
        if sign_text is None:
            return sign_state
        return "".join(
            (
                escape_code,
                sign_text[:1],
                "\x1b[m",
                "".join(("\x1b[90m", sign_text[1:], "\x1b[m")) if len(sign_text) > 1 else "",
            )
        )

    commit_char = COMMIT_CHAR_UNICODE if is_locale_utf8() else COMMIT_CHAR_ASCII
    line_regex = re.compile(r"([^\*]*)\*([^()]*\x1b[^m]*m)([0-9a-f]+)(\x1b[^m]*m.*)(.)$")
    for line in git_log_iterator:
        line = line.rstrip()
        match_obj = line_regex.match(line)
        if match_obj is not None:
            line_start, before_commit_hash, commit_hash, rest_of_line, sign_state = match_obj.groups()
            color_rgb_tuple = tuple(int(commit_hash[i : i + 2], base=16) for i in range(0, 6, 2))
            true_color_escape_sequence = "\x1b[38;2;{r:d};{g:d};{b:d}m".format(
                r=color_rgb_tuple[0], g=color_rgb_tuple[1], b=color_rgb_tuple[2]
            )
            colored_line = "".join(
                [
                    line_start,
                    true_color_escape_sequence,
                    commit_char,
                    "\x1b[m",
                    before_commit_hash,
                    commit_hash,
                    rest_of_line,
                    colorize_sign_state(sign_state),
                ]
            )
            yield colored_line
        else:
            yield line


def print_git_log(colorized_log_iterator: Iterator[str]) -> None:
    pager_with_options = get_pager_with_options()
    pager_process = subprocess.Popen(pager_with_options, stdin=subprocess.PIPE)
    try:
        for line in colorized_log_iterator:
            pager_process.stdin.write(encode("{}\n".format(line)))
            pager_process.stdin.flush()
        pager_process.stdin.close()
    except BrokenPipeError:
        pass
    returncode = pager_process.wait()
    if returncode != 0:
        raise PagerError(returncode)


def print_version() -> None:
    print("git clog version {}".format(__version__))


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-V", "--version"):
            print_version()
            sys.exit()
        else:
            print('Unknown command line argument "{}"'.format(sys.argv[1]))
            sys.exit(1)
    try:
        git_log_generator = gen_git_log()
        colorized_log_generator = gen_colorized_git_log_output(git_log_generator)
        print_git_log(colorized_log_generator)
    except (GitLogError, PagerError) as e:
        sys.exit(e.returncode)
    sys.exit()


if __name__ == "__main__":
    main()
