import base64
from typing import List

import opp

from saleor import settings
from ... import TransactionKind
from ...interface import (
    CustomerSource,
    GatewayConfig,
    GatewayResponse,
    PaymentData,
    PaymentMethodInfo,
)
from .utils import (
    get_amount_for_stripe,
    get_amount_from_stripe,
    get_currency_for_stripe,
    get_currency_from_stripe,
    shipping_to_stripe_dict,
)

success_codes = (
    '000.000.000',
    '000.000.100',
    '000.100.110',
    '000.100.111',
    '000.100.112',
    '000.300.000',
    '000.300.100',
    '000.300.101',
    '000.300.102'
)

DEBUG_CURRENCY = "USD"


def decode_b64_string(string):
    base64_bytes = string.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)

    return message_bytes.decode('ascii')


def get_client_token(**_):
    return


def authorize(
        payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:

    client = _get_client(**config.connection_params)
    
    try:
        response = client.checkouts(checkout_id=payment_information.token).get()
        gateway_response = _success_response(
            success=True if response['result']['code'] in success_codes else False,
            amount=payment_information.amount,
            currency=DEBUG_CURRENCY,
            customer_id=payment_information.customer_id or None,
            kind=TransactionKind.AUTH,
            raw_response=response,
        )
        return gateway_response
    except:
        print("Error in processing payment")
        return _error_response(kind=TransactionKind.AUTH, payment_info=payment_information, action_required=False)
    
def capture(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    client = _get_client(**config.connection_params)
    try:
        response = client.payments(payment_id=payment_information.token).create(**{
            "paymentType": "CP",
            "amount": "%0.2f" % payment_information.amount,
            "currency": DEBUG_CURRENCY
        })
        gateway_response = _success_response(
            success=True if response['result']['code'] in success_codes else False,
            amount=payment_information.amount,
            currency=payment_information.currency,
            customer_id=payment_information.customer_id or None,
            kind=TransactionKind.CAPTURE,
            raw_response=response,
        )
        return gateway_response
    except Exception as e:
        print("Error in processing payment")
        raise e
        return _error_response(
            kind=TransactionKind.CAPTURE_FAILED, 
            payment_info=payment_information, 
            action_required=False,
            exc=e
        )


def confirm(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    """Perform confirm transaction."""
    
    print("Capturing the remainder")
    return capture(payment_information, config)


def refund(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    client = _get_client(**config.connection_params)
    try:
        response = client.payments(payment_id=payment_information.token).create(**{
            "paymentType": "RF",
            "amount": "%0.2f" % payment_information.amount,
            "currency": DEBUG_CURRENCY
        })
        gateway_response = _success_response(
            success=True if response['result']['code'] in success_codes else False,
            amount=payment_information.amount,
            currency=payment_information.currency,
            customer_id=payment_information.customer_id or None,
            kind=TransactionKind.VOID,
            raw_response=response,
        )
        return gateway_response
    except Exception as e:
        print("Error in processing payment")
        raise e
        return _error_response(
            kind=TransactionKind.AUTH, 
            payment_info=payment_information, 
            action_required=False,
            exc=e
        )

def void(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    client = _get_client(**config.connection_params)
    
    try:
        response = client.payments(payment_id=payment_information.token).create(**{
            "paymentType": "RV",
            "amount": "%0.2f" % payment_information.amount,
            "currency": DEBUG_CURRENCY
        })
        gateway_response = _success_response(
            success=True if response['result']['code'] in success_codes else False,
            amount=payment_information.amount,
            currency=payment_information.currency,
            customer_id=payment_information.customer_id or None,
            kind=TransactionKind.VOID,
            raw_response=response,
        )
        return gateway_response
    except Exception as e:
        print("Error in processing payment")
        raise e
        return _error_response(
            kind=TransactionKind.AUTH, 
            payment_info=payment_information, 
            action_required=False,
            exc=e
        )


def list_client_sources(
        config: GatewayConfig, customer_id: str
) -> List[CustomerSource]:
    pass


def process_payment(
        payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    return authorize(payment_information, config)


def _get_client(**connection_params):
    opp.config.configure(mode=0 if settings.DEBUG else 3)
    return opp.core.API(
        **{"authentication.userId": connection_params.get("userId"),
           "authentication.password": connection_params.get("password"),
           "authentication.entityId": connection_params.get("entityId")
           })


def _error_response(
        kind: str,  # use TransactionKind class
        exc,
        payment_info: PaymentData,
        action_required: bool = False,
) -> GatewayResponse:
    return GatewayResponse(
        is_success=False,
        action_required=action_required,
        transaction_id=payment_info.token,
        amount=payment_info.amount,
        currency=payment_info.currency,
        error=exc,
        kind=kind,
        raw_response={},
        customer_id=payment_info.customer_id,
    )


def _success_response(
        kind: str,  # use TransactionKind class
        success: bool = True,
        amount=None,
        currency=None,
        customer_id=None,
        raw_response=None,
):
    currency = currency
    return GatewayResponse(
        is_success=success,
        action_required=False if success else True,
        transaction_id=raw_response['id'] if "id" in raw_response else "",
        amount=amount,
        currency=currency,
        error=None,
        kind=kind,
        raw_response=raw_response,
        customer_id=customer_id,
    )
