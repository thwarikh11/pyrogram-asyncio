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

import html

import pyrogram
from pyrogram.api import types

from .chat_photo import ChatPhoto
from .user_status import UserStatus
from ..object import Object


class User(Object):
    """A Telegram user or bot.

    Parameters:
        id (``int``):
            Unique identifier for this user or bot.

        is_self(``bool``):
            True, if this user is you yourself.

        is_contact(``bool``):
            True, if this user is in your contacts.

        is_mutual_contact(``bool``):
            True, if you both have each other's contact.

        is_deleted(``bool``):
            True, if this user is deleted.

        is_bot (``bool``):
            True, if this user is a bot.

        is_verified (``bool``):
            True, if this user has been verified by Telegram.

        is_restricted (``bool``):
            True, if this user has been restricted. Bots only.
            See *restriction_reason* for details.

        is_scam (``bool``):
            True, if this user has been flagged for scam.

        is_support (``bool``):
            True, if this user is part of the Telegram support team.

        first_name (``str``):
            User's or bot's first name.

        status (:obj:`UserStatus <pyrogram.UserStatus>`, *optional*):
            User's Last Seen status. Empty for bots.

        last_name (``str``, *optional*):
            User's or bot's last name.

        username (``str``, *optional*):
            User's or bot's username.

        language_code (``str``, *optional*):
            IETF language tag of the user's language.

        phone_number (``str``, *optional*):
            User's phone number.

        photo (:obj:`ChatPhoto <pyrogram.ChatPhoto>`, *optional*):
            User's or bot's current profile photo. Suitable for downloads only.

        restriction_reason (``str``, *optional*):
            The reason why this bot might be unavailable to some users.
            This field is available only in case *is_restricted* is True.
    """

    __slots__ = [
        "id", "is_self", "is_contact", "is_mutual_contact", "is_deleted", "is_bot", "is_verified", "is_restricted",
        "is_scam", "is_support", "first_name", "last_name", "status", "username", "language_code", "phone_number",
        "photo", "restriction_reason"
    ]

    def __init__(
        self,
        *,
        client: "pyrogram.BaseClient" = None,
        id: int,
        is_self: bool,
        is_contact: bool,
        is_mutual_contact: bool,
        is_deleted: bool,
        is_bot: bool,
        is_verified: bool,
        is_restricted: bool,
        is_scam: bool,
        is_support: bool,
        first_name: str,
        last_name: str = None,
        status: UserStatus = None,
        username: str = None,
        language_code: str = None,
        phone_number: str = None,
        photo: ChatPhoto = None,
        restriction_reason: str = None
    ):
        super().__init__(client)

        self.id = id
        self.is_self = is_self
        self.is_contact = is_contact
        self.is_mutual_contact = is_mutual_contact
        self.is_deleted = is_deleted
        self.is_bot = is_bot
        self.is_verified = is_verified
        self.is_restricted = is_restricted
        self.is_scam = is_scam
        self.is_support = is_support
        self.first_name = first_name
        self.last_name = last_name
        self.status = status
        self.username = username
        self.language_code = language_code
        self.phone_number = phone_number
        self.photo = photo
        self.restriction_reason = restriction_reason

    def __format__(self, format_spec):
        if format_spec == "mention":
            return '<a href="tg://user?id={0}">{1}</a>'.format(self.id, html.escape(self.first_name))

        return html.escape(str(self))

    @staticmethod
    def _parse(client, user: types.User) -> "User" or None:
        if user is None:
            return None

        return User(
            id=user.id,
            is_self=user.is_self,
            is_contact=user.contact,
            is_mutual_contact=user.mutual_contact,
            is_deleted=user.deleted,
            is_bot=user.bot,
            is_verified=user.verified,
            is_restricted=user.restricted,
            is_scam=user.scam,
            is_support=user.support,
            first_name=user.first_name,
            last_name=user.last_name,
            status=UserStatus._parse(client, user.status, user.id, user.bot),
            username=user.username,
            language_code=user.lang_code,
            phone_number=user.phone,
            photo=ChatPhoto._parse(client, user.photo, user.id),
            restriction_reason=user.restriction_reason,
            client=client
        )

    async def archive(self):
        """Bound method *archive* of :obj:`User`.

        Use as a shortcut for:

        .. code-block:: python

            client.archive_chats(123456789)

        Example:
            .. code-block:: python

                user.archive()

        Returns:
            True on success.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """

        return await self._client.archive_chats(self.id)

    async def unarchive(self):
        """Bound method *unarchive* of :obj:`User`.

        Use as a shortcut for:

        .. code-block:: python

            client.unarchive_chats(123456789)

        Example:
            .. code-block:: python

                user.unarchive()

        Returns:
            True on success.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """

        return await self._client.unarchive_chats(self.id)
