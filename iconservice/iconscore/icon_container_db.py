# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from collections import Iterator
from typing import TypeVar, Optional, Any, Union, TYPE_CHECKING

from ..base.address import Address
from ..base.exception import ContainerDBException
from ..icon_constant import DATA_BYTE_ORDER
from ..utils import int_to_bytes

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)


ARRAY_DB_ID = b'\x00'
DICT_DB_ID = b'\x01'
VAR_DB_ID = b'\x02'
LINKEDLIST_DB_ID = b'\x03'


class ContainerUtil(object):

    @staticmethod
    def create_db_prefix(cls, var_key: K) -> bytes:
        """Create a prefix used
        as a parameter of IconScoreDatabase.get_sub_db()

        :param cls: ArrayDB, DictDB, VarDB
        :param var_key:
        :return:
        """
        if var_key is None:
            raise ContainerDBException('key is None')

        if cls == ArrayDB:
            container_id = ARRAY_DB_ID
        elif cls == DictDB:
            container_id = DICT_DB_ID
        elif cls == LinkedListDB:
            container_id = LINKEDLIST_DB_ID
        else:
            raise ContainerDBException(f'Unsupported container class: {cls}')

        encoded_key: bytes = ContainerUtil.__encode_key(var_key)
        return b'|'.join([container_id, encoded_key])

    @staticmethod
    def encode_key(key: K) -> bytes:
        """Create a key passed to IconScoreDatabase

        :param key:
        :return:
        """
        if key is None:
            raise ContainerDBException('key is None')

        return ContainerUtil.__encode_key(key)

    @staticmethod
    def encode_value(value: V) -> bytes:
        return ContainerUtil.__encode_value(value)

    @staticmethod
    def __encode_key(key: K) -> bytes:
        if isinstance(key, int):
            bytes_key = int_to_bytes(key)
        elif isinstance(key, str):
            bytes_key = key.encode('utf-8')
        elif isinstance(key, Address):
            bytes_key = key.to_bytes()
        elif isinstance(key, bytes):
            bytes_key = key
        else:
            raise ContainerDBException(f"can't encode key: {key}")
        return bytes_key

    @staticmethod
    def __encode_value(value: V) -> bytes:
        if isinstance(value, int):
            byte_value = int_to_bytes(value)
        elif isinstance(value, str):
            byte_value = value.encode('utf-8')
        elif isinstance(value, Address):
            byte_value = value.to_bytes()
        elif isinstance(value, bool):
            byte_value = int_to_bytes(int(value))
        elif isinstance(value, bytes):
            byte_value = value
        else:
            raise ContainerDBException(f"can't encode value: {value}")
        return byte_value

    @staticmethod
    def decode_object(value: bytes, value_type: type) -> Optional[Union[K, V]]:
        if value is None:
            return get_default_value(value_type)

        obj_value = None
        if value_type == int:
            obj_value = int.from_bytes(value, DATA_BYTE_ORDER, signed=True)
        elif value_type == str:
            obj_value = value.decode()
        elif value_type == Address:
            obj_value = Address.from_bytes(value)
        if value_type == bool:
            obj_value = bool(int(int.from_bytes(value, DATA_BYTE_ORDER, signed=True)))
        elif value_type == bytes:
            obj_value = value
        return obj_value

    @staticmethod
    def remove_prefix_from_iters(iter_items: iter) -> iter:
        return ((ContainerUtil.__remove_prefix_from_key(key), value) for key, value in iter_items)

    @staticmethod
    def __remove_prefix_from_key(key_from_bytes: bytes) -> bytes:
        return key_from_bytes[:-1]

    @staticmethod
    def put_to_db(db: 'IconScoreDatabase', db_key: str, container: iter) -> None:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        if isinstance(container, dict):
            ContainerUtil.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            ContainerUtil.__put_to_db_internal(sub_db, enumerate(container))

    @staticmethod
    def get_from_db(db: 'IconScoreDatabase', db_key: str, *args, value_type: type) -> Optional[K]:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(arg))

        byte_key = sub_db.get(ContainerUtil.encode_key(last_arg))
        if byte_key is None:
            return get_default_value(value_type)
        return ContainerUtil.decode_object(byte_key, value_type)

    @staticmethod
    def __put_to_db_internal(db: 'IconScoreDatabase', iters: iter) -> None:
        for key, value in iters:
            sub_db = db.get_sub_db(ContainerUtil.encode_key(key))
            if isinstance(value, dict):
                ContainerUtil.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                ContainerUtil.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = ContainerUtil.encode_key(key)
                db_value = ContainerUtil.encode_value(value)
                db.put(db_key, db_value)


class DictDB(object):
    """
    Utility classes wrapping the state DB.
    DictDB behaves more like python dict. DictDB does not maintain order
    """

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type, depth: int=1) -> None:

        prefix: bytes = ContainerUtil.create_db_prefix(type(self), var_key)
        self._db = db.get_sub_db(prefix)

        self.__value_type = value_type
        self.__depth = depth

    def remove(self, key: K) -> None:
        """
        Removes the value of given key

        :param key: key
        """
        self.__remove(key)

    def __setitem__(self, key: K, value: V) -> None:
        if self.__depth != 1:
            raise ContainerDBException(f'DictDB depth mismatch')

        encoded_key: bytes = ContainerUtil.encode_key(key)
        encoded_value: bytes = ContainerUtil.encode_value(value)

        self._db.put(encoded_key, encoded_value)

    def __getitem__(self, key: K) -> Any:
        if self.__depth == 1:
            return ContainerUtil.decode_object(self._db.get(ContainerUtil.encode_key(key)), self.__value_type)
        else:
            return DictDB(key, self._db, self.__value_type, self.__depth - 1)

    def __delitem__(self, key):
        self.__remove(key)

    def __contains__(self, key: K):
        # Plyvel doesn't allow setting None value in the DB.
        # so there is no case of returning None value if the key exists.
        value = self._db.get(ContainerUtil.encode_key(key))
        return value is not None

    def __remove(self, key: K) -> None:
        if self.__depth != 1:
            raise ContainerDBException(f'DictDB depth mismatch')
        self._db.delete(ContainerUtil.encode_key(key))


class ArrayDB(Iterator):
    """
    Utility classes wrapping the state DB.
    supports length and iterator, maintains order
    """

    __SIZE = 'size'
    __SIZE_BYTE_KEY = ContainerUtil.encode_key(__SIZE)

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        prefix: bytes = ContainerUtil.create_db_prefix(type(self), var_key)
        self._db = db.get_sub_db(prefix)

        self.__size = self.__get_size()
        self.__index = 0
        self.__value_type = value_type

    def put(self, value: V) -> None:
        """
        Puts the value at the end of array

        :param value: value to add
        """
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(ContainerUtil.encode_key(self.__size), byte_value)
        self.__size += 1
        self.__set_size()

    def pop(self) -> Optional[V]:
        """
        Gets and removes last added value

        :return: last added value
        """
        if self.__size == 0:
            return None

        index = self.__size - 1
        last_val = self[index]
        self._db.delete(ContainerUtil.encode_key(index))
        self.__size -= 1
        self.__set_size()
        return last_val

    def get(self, index: int=0) -> V:
        """
        Gets the value at index

        :param index: index
        :return: value at the index
        """
        return self[index]

    def __iter__(self):
        self.__index = 0
        return self

    def __next__(self) -> V:
        if self.__index < self.__size:
            index = self.__index
            self.__index += 1
            return self[index]
        else:
            raise StopIteration

    def __len__(self):
        return self.__size

    def __get_size(self) -> int:
        return ContainerUtil.decode_object(self._db.get(ArrayDB.__SIZE_BYTE_KEY), int)

    def __set_size(self) -> None:
        sub_db = self._db
        byte_value = ContainerUtil.encode_value(self.__size)
        sub_db.put(ArrayDB.__SIZE_BYTE_KEY, byte_value)

    def __setitem__(self, index: int, value: V) -> None:
        if index >= self.__size:
            raise ContainerDBException(f'ArrayDB out of range')
        sub_db = self._db
        byte_value = ContainerUtil.encode_value(value)
        sub_db.put(ContainerUtil.encode_key(index), byte_value)

    def __getitem__(self, index: int) -> V:
        if isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                raise ContainerDBException(f'ArrayDB out of range, {index}')
            sub_db = self._db
            index_byte_key = ContainerUtil.encode_key(index)
            return ContainerUtil.decode_object(sub_db.get(index_byte_key), self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False


import struct


class LinkedListDB(object):
    __NODE_ID= 'node_id'
    __SIZE_ID = 'size_id'
    __HEAD_NODE_ID = 'head_node_id'
    __TAIL_NODE_ID = 'tail_node_id'

    __NODE_ID_BYTE_KEY = __NODE_ID.encode('utf-8')
    __SIZE_ID_BYTE_KEY = __SIZE_ID.encode('utf-8')
    __HEAD_ID_BYTE_KEY = __HEAD_NODE_ID.encode('utf-8')
    __TAIL_ID_BYTE_KEY = __TAIL_NODE_ID.encode('utf-8')

    class Node(object):
        __STRUCT_FMT = f'>BB'

        def __init__(self,
                     node_prev: int,
                     node_next: int,
                     node_data: bytes,
                     node_id: int = 0):
            self.prev = node_prev
            self.next = node_next
            self._data = node_data
            self.id = node_id

        def encode(self) -> bytes:
            if self.id == 0:
                raise ContainerDBException(f"Invalid id: can't use id")

            prev_bytes = int_to_bytes(self.prev)
            prev_bytes_length = len(prev_bytes)
            next_bytes = int_to_bytes(self.next)
            next_bytes_length = len(next_bytes)

            ret = struct.pack(LinkedListDB.Node.__STRUCT_FMT, prev_bytes_length, next_bytes_length)
            return ret + prev_bytes + next_bytes + self._data

        def convert_data(self, value_type: type) -> V:
            return ContainerUtil.decode_object(self._data, value_type)

        @staticmethod
        def decode(data: bytes) -> 'LinkedListDB.Node':
            length_bytes = data[:2]
            prev_bytes_length, next_bytes_length = struct.unpack(LinkedListDB.Node.__STRUCT_FMT, length_bytes)
            prev_bytes = data[2:2 + prev_bytes_length]
            next_bytes = data[2 + prev_bytes_length:2 + prev_bytes_length+next_bytes_length]
            node_bytes = data[2 + prev_bytes_length+next_bytes_length:]

            node_prev = int.from_bytes(prev_bytes, DATA_BYTE_ORDER, signed=True)
            node_next = int.from_bytes(next_bytes, DATA_BYTE_ORDER, signed=True)

            return LinkedListDB.Node(node_prev, node_next, node_bytes)

        @staticmethod
        def create_node(node_data: bytes) -> 'LinkedListDB.Node':
            return LinkedListDB.Node(0, 0, node_data)

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        prefix: bytes = ContainerUtil.create_db_prefix(type(self), var_key)
        self._db = db.get_sub_db(prefix)
        self._value_type = value_type

    def add_first(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        new_node = LinkedListDB.Node.create_node(byte_value)
        self._add(0, new_node)

    def add_last(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        new_node = LinkedListDB.Node.create_node(byte_value)
        self._add(-1, new_node)

    def add(self, index: int, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        new_node = LinkedListDB.Node.create_node(byte_value)
        self._add(index, new_node)

    def _add(self, index: int, new_node: 'LinkedListDB.Node') -> None:
        node_id: int = self._get_variable(LinkedListDB.__NODE_ID_BYTE_KEY)
        new_node.id = node_id + 1

        head_id = self._get_variable(LinkedListDB.__HEAD_ID_BYTE_KEY)
        tail_id = self._get_variable(LinkedListDB.__TAIL_ID_BYTE_KEY)
        size = self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)

        if index > size:
            raise ContainerDBException(f'LinkedListDB out of range')

        # reverse index
        if index < 0:
            index += size + 1

        if size == 0:
            LinkedListDB._set_node_to_db(self._db, new_node)
            self._set_variable(LinkedListDB.__HEAD_ID_BYTE_KEY, new_node.id)
            self._set_variable(LinkedListDB.__TAIL_ID_BYTE_KEY, new_node.id)
        elif index == size:
            # append
            prev_node = self._get_node_by_index(self._db, head_id, tail_id, size, index - 1)
            prev_node.next = new_node.id
            new_node.prev = prev_node.id

            LinkedListDB._set_node_to_db(self._db, prev_node)
            LinkedListDB._set_node_to_db(self._db, new_node)
            self._set_variable(LinkedListDB.__TAIL_ID_BYTE_KEY, new_node.id)
        else:
            # insert
            next_node = self._get_node_by_index(self._db, head_id, tail_id, size, index)
            prev_node = self._get_node_by_id(self._db, next_node.prev)

            next_node.prev = new_node.id
            new_node.next = next_node.id

            if prev_node is not None:
                prev_node.next = new_node.id
                new_node.prev = prev_node.id
            else:
                self._set_variable(LinkedListDB.__HEAD_ID_BYTE_KEY, new_node.id)

            LinkedListDB._set_node_to_db(self._db, prev_node)
            LinkedListDB._set_node_to_db(self._db, next_node)
            LinkedListDB._set_node_to_db(self._db, new_node)

        next_size: int = size + 1
        self._set_variable(LinkedListDB.__NODE_ID_BYTE_KEY, new_node.id)
        self._set_variable(LinkedListDB.__SIZE_ID_BYTE_KEY, next_size)

    def remove_first(self) -> None:
        self._remove(0)

    def remove_last(self) -> None:
        self._remove(-1)

    def remove(self, index: int) -> None:
        self._remove(index)

    def _remove(self, index: int) -> None:
        head_id = self._get_variable(LinkedListDB.__HEAD_ID_BYTE_KEY)
        tail_id = self._get_variable(LinkedListDB.__TAIL_ID_BYTE_KEY)
        size = self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)

        if index >= size:
            raise ContainerDBException(f'LinkedListDB out of range')

        if index < 0:
            index += size

        if size == 1:
            self._db.delete(ContainerUtil.encode_key(head_id))
            self._set_variable(LinkedListDB.__HEAD_ID_BYTE_KEY, 0)
            self._set_variable(LinkedListDB.__TAIL_ID_BYTE_KEY, 0)
        elif index == size - 1:
            # tail remove
            remove_node = self._get_node_by_index(self._db, head_id, tail_id, size, index)
            prev_node = self._get_node_by_id(self._db, remove_node.prev)
            prev_node.next = 0

            LinkedListDB._set_node_to_db(self._db, prev_node)
            self._db.delete(ContainerUtil.encode_key(remove_node.id))
            self._set_variable(LinkedListDB.__TAIL_ID_BYTE_KEY, prev_node.id)
        else:
            # remove
            remove_node = self._get_node_by_index(self._db, head_id, tail_id, size, index)
            prev_node = self._get_node_by_id(self._db, remove_node.prev)
            next_node = self._get_node_by_id(self._db, remove_node.next)

            if prev_node is not None and next_node is not None:
                prev_node.next = next_node.id
                next_node.prev = prev_node.id
            elif prev_node is None:
                next_node.prev = 0
                self._set_variable(LinkedListDB.__HEAD_ID_BYTE_KEY, next_node.id)
            else:
                prev_node.next = 0
                self._set_variable(LinkedListDB.__TAIL_ID_BYTE_KEY, prev_node.id)

            LinkedListDB._set_node_to_db(self._db, prev_node)
            LinkedListDB._set_node_to_db(self._db, next_node)
            self._db.delete(ContainerUtil.encode_key(remove_node.id))

        next_size: int = size - 1
        self._set_variable(LinkedListDB.__SIZE_ID_BYTE_KEY, next_size)

    def _get_variable(self, db_key: bytes) -> int:
        return ContainerUtil.decode_object(self._db.get(db_key), int)

    def _set_variable(self, db_key: bytes, value: int) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(db_key, byte_value)

    def __iter__(self):
        head_id = self._get_variable(LinkedListDB.__HEAD_ID_BYTE_KEY)
        size = self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)
        return self._get_generator(self._db, head_id, size)

    def reverse(self):
        tail_id = self._get_variable(LinkedListDB.__TAIL_ID_BYTE_KEY)
        size = self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)
        return self._get_generator(self._db, tail_id, size, True)

    def __len__(self):
        return self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)

    def __contains__(self, item: V):
        for e in self:
            if e.convert_data(self._value_type) == item:
                return True
        return False

    def __getitem__(self, index: int) -> V:
        head_id = self._get_variable(LinkedListDB.__HEAD_ID_BYTE_KEY)
        tail_id = self._get_variable(LinkedListDB.__TAIL_ID_BYTE_KEY)
        size = self._get_variable(LinkedListDB.__SIZE_ID_BYTE_KEY)

        target_node = self._get_node_by_index(self._db, head_id, tail_id, size, index)
        return target_node.convert_data(self._value_type)

    @staticmethod
    def _set_node_to_db(db: 'IconScoreDatabase', node: Optional['LinkedListDB.Node']) -> None:
        if node is None:
            return

        byte_node_data: bytes = node.encode()
        db.put(ContainerUtil.encode_key(node.id), byte_node_data)

    @staticmethod
    def _get_node_by_id(db: 'IconScoreDatabase', node_id: int) -> Optional['LinkedListDB.Node']:
        bytes_node_id = ContainerUtil.encode_key(node_id)
        bytes_node_data = db.get(bytes_node_id)
        if bytes_node_data is None:
            return None
        else:
            node = LinkedListDB.Node.decode(bytes_node_data)
            node.id = node_id
            return node

    @staticmethod
    def _get_node_by_index(db: 'IconScoreDatabase',
                           head_id: int,
                           tail_id: int,
                           size: int,
                           index: int) -> Optional['LinkedListDB.Node']:

        if index >= size:
            raise ContainerDBException(f'LinkedListDB out of range')

        if size == 0:
            return None

        if index < 0:
            index += size

        if index > size // 2:
            is_reverse = True
            start_id = tail_id
            index = size - index - 1
        else:
            is_reverse = False
            start_id = head_id

        gen = LinkedListDB._get_generator(db, start_id, size, is_reverse)
        target_node = next(gen)

        for _ in range(index):
            target_node = next(gen)
        return target_node

    @staticmethod
    def _get_generator(db: 'IconScoreDatabase', start_id: int, size: int, is_reverse: bool = False):
        next_id = start_id

        for _ in range(size):
            node = LinkedListDB._get_node_by_id(db, next_id)
            if is_reverse is True:
                next_id = node.prev
            else:
                next_id = node.next
            yield node


class VarDB(object):
    """
    Utility classes wrapping the state DB. can be used to store simple key-value state
    """

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        # Use var_key as a db prefix in the case of VarDB
        self._db = db.get_sub_db(VAR_DB_ID)

        self.__var_byte_key = ContainerUtil.encode_key(var_key)
        self.__value_type = value_type

    def set(self, value: V) -> None:
        """
        Sets the value

        :param value: a value to be set
        """
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(self.__var_byte_key, byte_value)

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        return ContainerUtil.decode_object(self._db.get(self.__var_byte_key), self.__value_type)

    def remove(self) -> None:
        """
        Deletes the value
        """
        self._db.delete(self.__var_byte_key)


def get_default_value(value_type: type) -> Any:
    if value_type == int:
        return 0
    elif value_type == str:
        return ""
    elif value_type == bool:
        return False
    return None
