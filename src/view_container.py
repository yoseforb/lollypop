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

from gi.repository import Gtk, GLib

from lollypop.view_device import DeviceView

# Container for a view
# Can contain any other widget too
class ViewContainer(Gtk.Stack):
    def __init__(self, duration):
        Gtk.Stack.__init__(self)
        self.set_property("expand", True)
        self._duration = duration
        # Don't pass resize request to parent
        self.set_resize_mode(Gtk.ResizeMode.QUEUE)
        self.set_transition_duration(duration)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    """
        Clean old views
        @param view as new View
    """
    def clean_old_views(self, view):
        for child in self.get_children():
            if child != view:
                if hasattr(child, "stop"):
                    child.stop()
                if isinstance(child, DeviceView):
                    self.remove(child)
                else:
                    # Delayed destroy as we may have an animation running
                    # Gtk.StackTransitionType.CROSSFADE
                    GLib.timeout_add(self._duration,
                                     self._delayedclean_view,
                                     child)

#######################
# PRIVATE             #
#######################
    """
        Clean view
        @param valid view as View
    """
    def _delayedclean_view(self, view):
        if hasattr(view, "remove_signals"):
            view.remove_signals()
        view.destroy()