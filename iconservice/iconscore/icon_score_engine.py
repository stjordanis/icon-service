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
"""IconScoreEngine module
"""

from typing import TYPE_CHECKING

from iconcommons.logger import Logger
from iconservice.icon_constant import IconScoreContextType
from .icon_score_context import IconScoreContext, IconScoreFuncType
from .icon_score_mapper import IconScoreMapper
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException
from ..base.type_converter import TypeConverter

if TYPE_CHECKING:
    from ..icx.icx_storage import IcxStorage
    from ..iconscore.icon_score_base import IconScoreBase


class IconScoreEngine(object):
    """Calls external functions provided by each IconScore
    """

    def __init__(self) -> None:
        """Constructor
        """
        super().__init__()

        self.__icx_storage = None
        self.__icon_score_mapper = None

    def open(self,
             icx_storage: 'IcxStorage',
             icon_score_mapper: 'IconScoreMapper') -> None:
        """open

        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_mapper:
        """
        self.__icx_storage = icx_storage
        self.__icon_score_mapper = icon_score_mapper

    def invoke(self,
               context: 'IconScoreContext',
               icon_score_address: 'Address',
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """

        if icon_score_address is None or \
                icon_score_address is ZERO_SCORE_ADDRESS or \
                not icon_score_address.is_contract:
            raise InvalidParamsException(f"invalid score address: ({icon_score_address})")

        context.validate_score_blacklist(icon_score_address)

        if data_type == 'call':
            self._call(context, icon_score_address, data)
        else:
            self._fallback(context, icon_score_address)

    def query(self,
              context: IconScoreContext,
              icon_score_address: Address,
              data_type: str,
              data: dict) -> object:
        """Execute an external method of SCORE without state changing

        Handles messagecall of icx_call
        """
        if icon_score_address is None or \
                icon_score_address is ZERO_SCORE_ADDRESS or \
                not icon_score_address.is_contract:
            raise InvalidParamsException(f"invalid score address: ({icon_score_address})")

        context.validate_score_blacklist(icon_score_address)

        if data_type == 'call':
            return self._call(context, icon_score_address, data)
        else:
            raise InvalidParamsException(f'Invalid dataType: ({data_type})')

    def get_score_api(self,
                      context: 'IconScoreContext',
                      icon_score_address: 'Address') -> object:
        """Handle get score api

        :param context:
        :param icon_score_address:
        """

        icon_score = self._get_icon_score(context, icon_score_address)
        return icon_score.get_api()

    def _call(self,
              context: 'IconScoreContext',
              icon_score_address: 'Address',
              data: dict) -> object:
        """Handle jsonrpc including both invoke and query

        :param context:
        :param icon_score_address:
        :param data: data to call the method of score
        """
        func_name: str = data['method']
        kw_params: dict = data.get('params', {})

        icon_score = self._get_icon_score(context, icon_score_address)

        is_func_readonly = getattr(icon_score, '_IconScoreBase__is_func_readonly')
        if func_name is not None and is_func_readonly(func_name):
            context.func_type = IconScoreFuncType.READONLY
        else:
            context.func_type = IconScoreFuncType.WRITABLE

        converted_params = self._convert_score_params_by_annotations(icon_score, func_name, kw_params)
        external_func = getattr(icon_score, '_IconScoreBase__external_call')
        return external_func(func_name=func_name, arg_params=[], kw_params=converted_params)

    @staticmethod
    def _convert_score_params_by_annotations(icon_score: 'IconScoreBase', func_name: str, kw_params: dict) -> dict:
        tmp_params = kw_params

        icon_score.validate_external_method(func_name)

        score_func = getattr(icon_score, func_name)
        annotation_params = TypeConverter.make_annotations_from_method(score_func)
        TypeConverter.convert_data_params(annotation_params, tmp_params)
        return tmp_params

    def _fallback(self,
                  context: 'IconScoreContext',
                  score_address: 'Address'):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param score_address:
        """
        icon_score = self._get_icon_score(context, score_address)

        fallback_func = getattr(icon_score, '_IconScoreBase__fallback_call')
        fallback_func()

    @staticmethod
    def _get_icon_score(context: 'IconScoreContext', icon_score_address: 'Address'):
        icon_score = context.get_icon_score(icon_score_address)
        if icon_score is None:
            raise ServerErrorException(
                f'SCORE not found: {icon_score_address}')

        IconScoreEngine._fix_mecacoin_member_variable_bug_on_mainnet(context, icon_score)
        # IconScoreEngine._fix_mecacoin_member_variable_bug_on_testnet(context, icon_score)

        return icon_score

    @staticmethod
    def _fix_mecacoin_member_variable_bug_on_mainnet(
            context: 'IconScoreContext', score: 'IconScoreBase'):
        """Initialize self.privateSaleHolder to prevent the score from raising an exception

        Resolve consensus failure, initializing an undefined member variable in meca coin
        This code is only available for mainnet.

        :param context:
        :param score:
        :return:
        """
        if context.type != IconScoreContextType.INVOKE:
            return

        block_height: int = context.block.height
        if block_height < 96562 or block_height > 119932:
            return

        meca_coin_address = Address.from_string('cxf9148db4f8ec78823a50cb06c4fed83660af38d0')
        if score.address != meca_coin_address:
            return

        if hasattr(score, 'privateSaleHolder'):
            return

        if block_height < 109911:
            score.privateSaleHolder = ''
        else:
            private_sale_token_holder_address = 'hx1534d888c4936966208a0aced276b0731547c091'
            score.privateSaleHolder = private_sale_token_holder_address

        Logger.warning(
            tag='MECA', msg=f'PrivateSaleHolder: {score.privateSaleHolder}')
        print(f'PrivateSaleHolder: {score.privateSaleHolder}')

    @staticmethod
    def _fix_mecacoin_member_variable_bug_on_testnet(
            context: 'IconScoreContext', score: 'IconScoreBase'):
        """Initialize self.privateSaleHolder to prevent the score from raising an exception

        Resolve consensus failure, initializing an undefined member variable in meca coin
        This code is only available for testnet.

        :param context:
        :param score:
        :return:
        """
        if context.type != IconScoreContextType.INVOKE:
            return

        block_height: int = context.block.height
        if block_height < 42469:
            return

        meca_coin_address = Address.from_string('cxf6df28536dbf33f7f2431178790a15e9d70cc79a')
        if score.address != meca_coin_address:
            return

        if not hasattr(score, 'privateSaleHolder'):
            raise ValueError
            return

        if block_height >= 42469:
            del score.privateSaleHolder

        # Logger.warning(tag='MECA', msg=f'Does score.privateSaleHolder exist?: {hasattr(score, "privateSaleHolder")}')
