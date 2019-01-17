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

"""IconScoreEngine testcase
"""

import unittest

from iconservice import IconServiceFlag
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateScores(TestIntegrateBase):

    def test_db_returns(self):
        tx1 = self._make_deploy_tx("test_scores",
                                   "test_db_returns",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 0)

        value = 1 * self._icx_factor
        tx2 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value2",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, "")

        value = "a"
        tx3 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": value})

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value3",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, None)

        value = self._prev_block_hash
        tx4 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": bytes.hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value4",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, self._addr_array[1])

        value = self._genesis
        tx5 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": str(value)})

        prev_block, tx_results = self._make_and_req_block([tx5])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value5",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, False)

        value = True
        tx6 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": hex(int(value))})

        prev_block, tx_results = self._make_and_req_block([tx6])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value6",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, self._addr_array[1])

        value = self._genesis
        tx7 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value6', {"value": str(value)})

        prev_block, tx_results = self._make_and_req_block([tx7])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

    def test_member_variable_score(self):
        _from: 'Address' = self._addr_array[0]

        tx: dict = self._make_deploy_tx(
            "test_scores", "test_member_variable_score", _from, ZERO_SCORE_ADDRESS)

        block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(block)

        self.assertEqual(tx_results[0].status, int(True))
        score_address: 'Address' = tx_results[0].score_address

        request = {
            "version": self._version,
            "from": _from,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "getName",
                "params": {}
            }
        }
        response = self._query(request)
        self.assertEqual(response, 'haha')


if __name__ == '__main__':
    unittest.main()
