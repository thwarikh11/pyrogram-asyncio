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

import pyrogram
from pyrogram.api import functions, types
from ...ext import BaseClient


class GetMe(BaseClient):
    async def get_me(self) -> "pyrogram.User":
        """Get your own user identity.

        Returns:
            :obj:`User`: Basic information about the user or bot.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """
        return pyrogram.User._parse(
            self,
            (await self.send(
                functions.users.GetFullUser(
                    id=types.InputPeerSelf()
                )
            )).user
        )
