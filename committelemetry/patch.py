# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Patch handling routines.
"""

# Mercurial export patches produced by 'hg export' or by the hgweb 'raw' view
# have the following structure.
#
#   HG_HEADER
#   HG_METADATA
#   COMMIT_DESCRIPTION
#   blank line
#   GIT_DIFF
#
# Where:
#
# HG_HEADER: One line starting with '#'.
#
# HG_METADATA: Multiple lines starting with '#'.
#
# COMMIT_DESCRIPTION: Multiple lines of plain ASCII text.  Blank lines in the commit
# description are allowed.  The mixed-in blank lines make it hard to tell where the
# commit description ends and the delimiter between the COMMIT_DESCRIPTION and
# GIT_DIFF sections begin.  And if a GIT_DIFF-formatted block of text *is* the commit
# message you summon Cthulhu (this is a known weakness in the format).
#
# GIT_DIFF: A Git Extended Diff formatted patch.
#     See https://git-scm.com/docs/diff-format#_generating_patches_with_p
#
# Here is an example patch generated by 'hg export --git'
#
#   # HG changeset patch
#   # User Māris Fogels <mars@mozilla.com>
#   # Date 1530120920 14400
#   #      Wed Jun 27 13:35:20 2018 -0400
#   # Node ID 62a578a28fe94efb7f03138bbfaa458d1c31314e
#   # Parent  3659a2ff799f0a531283d22d112b08eb23a9ced7
#   Fix capitalization
#
#   diff --git a/hello.txt b/hello.txt
#   --- a/hello.txt
#   +++ b/hello.txt
#   @@ -1,1 +1,1 @@
#   -hello world
#   +Hello World
#
# Git Diffs themselves are an extension to the Unified Diff format.  They consist of
# file headers starting with 'diff --git', followed by a number of extended header
# lines such as '+++' and '---'.  If the file is a text file, the file header and
# extended headers are followed by zero or more context diff hunks.
#
# Each context diff hunk is marked by a header line starting with the text '@@'.
# Each line of the hunk starts with a control character: ' ' for diff context lines (
# unmodified lines), '+' for lines added by the patch, and '-' for lines removed by
# the patch.
#
import io
from typing import NamedTuple


class DiffStat(NamedTuple):
    """A collection of patch file statistics.

    Attributes:
        files_changed: The number of files modified by a patch.
        additions: The total number of additions ('+' lines) in a patch.
        deletions: The total number of deletions ('-' lines) in a patch.
    """

    files_changed: int
    additions: int
    deletions: int


def diffstat(patch_text: str) -> DiffStat:
    """Return the number of additions and deletions in a patch.

    The count of additions and deletions returned should be the same as running
    'hg diff --git --stat' on a patch.

    The linecount of added and deleted files are included in the total.

    File renames do not count towards the total additions or deletions, but do count
    towards the changed files.  Binary file changes are also handled this way.

    One known issue is putting a patch body or hunk (lines starting with 'diff --git'
    or '@@ ') inside a 'hg export' commit description (the part before the real patch
    file starts).  This function may give slightly inflated counts in those cases.

    Args:
        patch_text: The text from either a 'hg export' patch or a Git Extended diff
            patch produced by something like 'hg diff --git'.

    Returns:
        A `DiffStat` object with the collected statistics.
    """
    additions = 0
    deletions = 0
    filecount = 0

    # StringIO is fast, similar in speed to BytesIO, for handling data under Python 3.
    # 'for line in somefile_or_buffer' is similarly fast, with a small memory
    # footprint, even for large files.
    patch_buffer = io.StringIO(patch_text)

    # Since we only want additions, deletions, and changed files we can search for
    # diff lines that start with 'diff', '+' and '-'.  We can ignore lines that start
    # with anything else.  When searching for '+' and '-' we must ignore all lines
    # outside of diff hunks.
    in_hunk = False
    for line in patch_buffer:
        if line.startswith('diff --git'):
            # We are starting the diff control section of a new diff in this patch.
            # The next few lines are patch control statements which we need to ignore.
            in_hunk = False
            filecount += 1
        elif line.startswith('@@ '):
            # Every line for the rest of this diff will start with a control
            # character of +, -, space, or @. It is now safe to start counting
            # additions and deletions.
            in_hunk = True
        elif in_hunk and line.startswith('+'):
            additions += 1
        elif in_hunk and line.startswith('-'):
            deletions += 1

    return DiffStat(additions, deletions, filecount)
