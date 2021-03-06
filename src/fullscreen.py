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

from gi.repository import Gtk, Gdk, GLib

from cgi import escape
from gettext import gettext as _

from lollypop.define import Lp, ArtSize, Type
from lollypop.utils import seconds_to_string


# Show a fullscreen window showing current track context
class FullScreen(Gtk.Window):

    """
        Init window and set transient for parent
        @param: parent as Gtk.window
    """
    def __init__(self, parent):
        Gtk.Window.__init__(self)
        self._timeout = None
        self._seeking = False
        self._signal1_id = None
        self._signal2_id = None
        self.set_transient_for(parent)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/FullScreen.ui')
        main_widget = builder.get_object('fs')
        self.add(main_widget)
        self._prev_btn = builder.get_object('prev_btn')
        self._prev_btn.connect('clicked', self._on_prev_btn_clicked)
        self._play_btn = builder.get_object('play_btn')
        self._play_btn.connect('clicked', self._on_play_btn_clicked)
        self._next_btn = builder.get_object('next_btn')
        self._next_btn.connect('clicked', self._on_next_btn_clicked)
        self._play_image = builder.get_object('play_image')
        self._pause_image = builder.get_object('pause_image')
        close_btn = builder.get_object('close_btn')
        close_btn.connect('clicked', self._destroy)
        self._cover = builder.get_object('cover')
        self._title = builder.get_object('title')
        self._artist = builder.get_object('artist')
        self._album = builder.get_object('album')
        self._next = builder.get_object('next')
        self._next_cover = builder.get_object('next_cover')

        self._progress = builder.get_object('progress_scale')
        self._progress.connect('button-release-event',
                               self._on_progress_release_button)
        self._progress.connect('button-press-event',
                               self._on_progress_press_button)
        self._timelabel = builder.get_object('playback')
        self._total_time_label = builder.get_object('duration')
        self.connect('key-release-event', self._on_key_release_event)

    """
        Init signals, set color and go party mode if nothing is playing
    """
    def do_show(self):
        is_playing = Lp.player.is_playing()
        self._signal1_id = Lp.player.connect('current-changed',
                                             self._on_current_changed)
        self._signal2_id = Lp.player.connect('status-changed',
                                             self._on_status_changed)
        if is_playing:
            self._change_play_btn_status(self._pause_image, _('Pause'))
            self._on_current_changed(Lp.player)
        else:
            Lp.player.set_party(True)
        if not self._timeout:
            self._timeout = GLib.timeout_add(1000, self._update_position)
        Gtk.Window.do_show(self)
        self._update_position()
        self.fullscreen()

    """
        Remove signals and unset color
    """
    def do_hide(self):
        if self._signal1_id:
            Lp.player.disconnect(self._signal1_id)
            self._signal1_id = None
        if self._signal2_id:
            Lp.player.disconnect(self._signal2_id)
            self._signal2_id = None
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

#######################
# PRIVATE             #
#######################
    """
        Update View for current track
            - Cover
            - artist/title
            - reset progress bar
            - update time/total labels
        @param player as Player
    """
    def _on_current_changed(self, player):
        if player.current_track.id is None:
            pass  # Impossible as we force play on show
        else:
            if Lp.player.current_track.id == Type.RADIOS:
                self._prev_btn.set_sensitive(False)
                self._next_btn.set_sensitive(False)
                self._timelabel.hide()
                self._total_time_label.hide()
                self._progress.hide()
                cover = Lp.art.get_radio(player.current_track.artist,
                                         ArtSize.MONSTER)
            else:
                self._prev_btn.set_sensitive(True)
                self._next_btn.set_sensitive(True)
                self._timelabel.show()
                self._total_time_label.show()
                self._progress.show()
                cover = Lp.art.get_album(player.current_track.album_id,
                                         ArtSize.MONSTER)

            self._cover.set_from_pixbuf(cover)
            del cover

            album = player.current_track.album
            if player.current_track.year != '':
                album += " (%s)" % player.current_track.year
            self._title.set_text(player.current_track.title)
            self._artist.set_text(player.current_track.artist)
            self._album.set_text(album)
            next_cover = Lp.art.get_album(player.next_track.album_id,
                                           ArtSize.MEDIUM)
            self._next_cover.set_from_pixbuf(next_cover)
            del next_cover
            self._next.set_markup("<b>%s</b> - %s" %
                                  (escape(player.next_track.artist),
                                   escape(player.next_track.title)))
            self._progress.set_value(1.0)
            self._progress.set_range(0.0, player.current_track.duration * 60)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))
            self._timelabel.set_text("0:00")

    """
        Destroy window if Esc
        @param widget as Gtk.Widget
        @param event as Gdk.event
    """
    def _on_key_release_event(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    """
        Go to prev track
        @param widget as Gtk.Button
    """
    def _on_prev_btn_clicked(self, widget):
        Lp.player.prev()

    """
        Play/pause
        @param widget as Gtk.Button
    """
    def _on_play_btn_clicked(self, widget):
        if Lp.player.is_playing():
            Lp.player.pause()
            widget.set_image(self._play_image)
        else:
            Lp.player.play()
            widget.set_image(self._pause_image)

    """
        Go to next track
        @param widget as Gtk.Button
    """
    def _on_next_btn_clicked(self, widget):
        Lp.player.next()

    """
        Update buttons and progress bar
        @param obj as unused
    """
    def _on_status_changed(self, obj):
        is_playing = Lp.player.is_playing()
        if is_playing and not self._timeout:
            self._timeout = GLib.timeout_add(1000, self._update_position)
            self._change_play_btn_status(self._pause_image, _("Pause"))
        elif not is_playing and self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None
            self._change_play_btn_status(self._play_image, _("Play"))

    """
        On press, mark player as seeking
        @param unused
    """
    def _on_progress_press_button(self, scale, data):
        self._seeking = True

    """
        Callback for scale release button
        Seek player to scale value
        @param scale as Gtk.Scale, data as unused
    """
    def _on_progress_release_button(self, scale, data):
        value = scale.get_value()
        self._seeking = False
        self._update_position(value)
        Lp.player.seek(value/60)

    """
        Update play button with image and status as tooltip
        @param image as Gtk.Image
        @param status as str
    """
    def _change_play_btn_status(self, image, status):
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

    """
        Update progress bar position
        @param value as int
    """
    def _update_position(self, value=None):
        if not self._seeking and self._progress.is_visible():
            if value is None:
                value = Lp.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True

    """
        Destroy self
        @param widget as Gtk.Button
    """
    def _destroy(self, widget):
        self.destroy()
