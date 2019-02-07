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

from iconservice.base.address import ZERO_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestScoreMemberVariable(TestIntegrateBase):

    def test_use_cached_score(self):
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
        self.assertEqual(response, 'on_install')

    def test_use_every_time_created_score(self):
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
        self.assertEqual(response, '__init__')


if __name__ == '__main__':
    unittest.main()
