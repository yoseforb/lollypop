#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject

from lollypop.define import PlayContext, Lp
from lollypop.track import Track


class BasePlayer(GObject.GObject):
    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'queue-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'party-changed': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }
    """
        Init base player variables
    """
    def __init__(self):
        # In case of multiple subclassing,
        # do not init variables for every subclass
        if not hasattr(self, '_albums'):
            GObject.GObject.__init__(self)
            self._base_init = True
            # A user playlist used as current playlist
            self._user_playlist = None
            # Used by shuffle tracks to restore user playlist before shuffle
            self._user_playlist_backup = None
            self.current_track = Track()
            self.next_track = Track()
            self.prev_track = Track()
            self.context = PlayContext()
            # Albums in current playlist
            self._albums = None
            # Current shuffle mode
            self._shuffle = Lp.settings.get_enum('shuffle')
            # For tracks from the cmd line
            self._external_tracks = []
            
#######################
# PRIVATE             #
#######################
    """
        Set next track
    """
    def _set_next(self):
        pass

    """
        Set prev track
    """
    def _set_prev(self):
        pass
