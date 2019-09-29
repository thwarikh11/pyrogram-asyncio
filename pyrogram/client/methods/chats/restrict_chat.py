# Pyrogram - Telegram MTProto API Client Library for Python
# Copyright (C) 2017-2019 Dan Tès <https://github.com/delivrance>
#
# This file is part of Pyrogram.
#
# Pyrogram is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pyrogram is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

from typing import Union

from pyrogram.api import functions, types
from ...ext import BaseClient
from ...types.user_and_chats import Chat


class RestrictChat(BaseClient):
    def restrict_chat(
        self,
        chat_id: Union[int, str],
        can_send_messages: bool = False,
        can_send_media_messages: bool = False,
        can_send_other_messages: bool = False,
        can_add_web_page_previews: bool = False,
        can_send_polls: bool = False,
        can_change_info: bool = False,
        can_invite_users: bool = False,
        can_pin_messages: bool = False
    ) -> Chat:
        """Restrict a chat.
        Pass True for all boolean parameters to lift restrictions from a chat.

        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.

            can_send_messages (``bool``, *optional*):
                Pass True, if the user can send text messages, contacts, locations and venues.

            can_send_media_messages (``bool``, *optional*):
                Pass True, if the user can send audios, documents, photos, videos, video notes and voice notes,
                implies can_send_messages.

            can_send_other_messages (``bool``, *optional*):
                Pass True, if the user can send animations, games, stickers and use inline bots,
                implies can_send_media_messages.

            can_add_web_page_previews (``bool``, *optional*):
                Pass True, if the user may add web page previews to their messages, implies can_send_media_messages.

            can_send_polls (``bool``, *optional*):
                Pass True, if the user can send polls, implies can_send_media_messages.

            can_change_info (``bool``, *optional*):
                Pass True, if the user can change the chat title, photo and other settings.

            can_invite_users (``bool``, *optional*):
                Pass True, if the user can invite new users to the chat.

            can_pin_messages (``bool``, *optional*):
                Pass True, if the user can pin messages.

        Returns:
            :obj:`Chat`: On success, a chat object is returned.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """
        send_messages = True
        send_media = True
        send_stickers = True
        send_gifs = True
        send_games = True
        send_inline = True
        embed_links = True
        send_polls = True
        change_info = True
        invite_users = True
        pin_messages = True

        if can_send_messages:
            send_messages = None

        if can_send_media_messages:
            send_messages = None
            send_media = None

        if can_send_other_messages:
            send_messages = None
            send_media = None
            send_stickers = None
            send_gifs = None
            send_games = None
            send_inline = None

        if can_add_web_page_previews:
            send_messages = None
            send_media = None
            embed_links = None

        if can_send_polls:
            send_messages = None
            send_polls = None

        if can_change_info:
            change_info = None

        if can_invite_users:
            invite_users = None

        if can_pin_messages:
            pin_messages = None

        r = self.send(
            functions.messages.EditChatDefaultBannedRights(
                peer=self.resolve_peer(chat_id),
                banned_rights=types.ChatBannedRights(
                    until_date=0,
                    send_messages=send_messages,
                    send_media=send_media,
                    send_stickers=send_stickers,
                    send_gifs=send_gifs,
                    send_games=send_games,
                    send_inline=send_inline,
                    embed_links=embed_links,
                    send_polls=send_polls,
                    change_info=change_info,
                    invite_users=invite_users,
                    pin_messages=pin_messages
                )
            )
        )

        return Chat._parse_chat(self, r.chats[0])
