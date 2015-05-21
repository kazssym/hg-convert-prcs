# prcs.py for convertprcs
# Copyright (C) 2015 Kaz Nishimura
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import re

# from hgext.convert.common import converter_source
from . import _convert
_common = __import__(
        _convert.__name__ + '.common', globals(), locals(),
        ['converter_source', 'commit'])
converter_source = _common.converter_source
commit = _common.commit

from prcslib import PrcsVersion, PrcsProject, PrcsError, PrcsCommandError

# Regular expression pattern that checks for main branches.
_MAIN_BRANCH_RE = re.compile(r"^(\d+)$")

class prcs_source(converter_source):
    """Import a PRCS project."""

    def __init__(self, ui, path=None, rev=None):
        super(prcs_source, self).__init__(ui, path, rev)

        try:
            self._prcs = PrcsProject(path)
            self._revision = self._prcs.revisions()
        except PrcsCommandError as error:
            ui.note(error.error_message)
            raise _common.NoRepo()
        except PrcsError:
            raise _common.NoRepo()

    def getheads(self):
        last_minor_version = {}
        for v in self._revision.iterkeys():
            if not self._revision[v]['deleted']:
                v = PrcsVersion(v)
                if last_minor_version.get(v.major, 0) < v.minor:
                    last_minor_version[v.major] = v.minor
        return map(
                lambda (major, minor): str(PrcsVersion(major, minor)),
                last_minor_version.iteritems())

    def getchanges(self, version, full=False):
        self.ui.debug("getchanges ", version, "\n")
        return [], {}

    def getcommit(self, version):
        self.ui.debug("getcommit ", version, "\n")
        revision = self._revision[version]
        descriptor = self._prcs.descriptor(version)

        parent = []
        p = descriptor.parentversion()
        if p is not None:
            if self._revision[str(p)]['deleted']:
                self.ui.debug("Parent version ", p, " was deleted\n")
                p = self._nearest_ancestor(p)
                self.ui.debug("The nearest version is ", p, "\n")
            if p is not None:
                parent.append(str(p))
        for p in descriptor.mergeparents():
            parent.append(p)

        branch = PrcsVersion(version).major
        if _MAIN_BRANCH_RE.match(branch):
            branch = None
        return commit(
                revision['author'], revision['date'].isoformat(" "),
                descriptor.message(), parent, branch)

    def _nearest_ancestor(self, version):
        """Return an indirect parent for a deleted version."""
        if isinstance(version, str):
            version = PrcsVersion(version)

        while self._revision[str(version)]['deleted']:
            version.minor -= 1
            if version.minor == 0:
                return None
        return version

    def gettags(self):
        """Return an empty dictionary since PRCS has no tags."""
        return {}
