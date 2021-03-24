import logging
import requests
import datetime

from django.http import (
    HttpResponseNotFound,
    JsonResponse,
    HttpResponse
)
from django.core.handlers.wsgi import WSGIRequest
from django.utils.text import slugify
from django.db import transaction
from ..base_plugin import BasePlugin
from ...product.models import Product, ProductType, ProductVariant, ProductTranslation, ProductChannelListing, Channel, ProductVariantChannelListing
from ...attribute.utils import associate_attribute_values_to_instance
from ...attribute.models import Attribute, AttributeValue, AttributeInputType, AttributeType

logger = logging.getLogger(__name__)

SYNC_URL = "http://83.136.252.92:8082/newparts"
SYNC_USERNAME = "ECOM"
SYNC_PASSWORD = "Ecom@2050"

class ProductSyncPlugin(BasePlugin):
    PLUGIN_ID = "elite_road.productsync"
    PLUGIN_NAME = "Elite Road Product Sync"
    DEFAULT_ACTIVE = True
    PLUGIN_DESCRIPTION = "Plugin to sync products from the external API"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("[Product Sync] Init")

    def _get_attribute(self, attribute_str, product_type):
        attribute, created = Attribute.objects.get_or_create(
            slug=slugify(attribute_str, allow_unicode=True),
            defaults={
                "type": AttributeType.PRODUCT_TYPE,
                "input_type": AttributeInputType.DROPDOWN,
                "name": attribute_str
            }
        )
        if created:
            attribute.product_types.add(product_type)

        return attribute

    def _get_attribute_value(self, attribute, attribute_value_str):
        attribute_value, created = AttributeValue.objects.get_or_create(
            slug=slugify(attribute_value_str, allow_unicode=True),
            defaults={
                "name": attribute_value_str,
                "value": attribute_value_str,
                "attribute": attribute
            }
        )

        return attribute_value

    @transaction.atomic
    def _add_product(self, product_data):
        # check if product exists
        product_variant_instance = ProductVariant.objects.filter(sku=product_data["sparepart"]).first()

        if product_variant_instance is not None:
            # only update pricing in this case 
            for variant_channel in product_variant_instance.channel_listings.all():
                variant_channel.price_amount = product_data["item_price"]
                variant_channel.cost_price_amount = product_data["item_price"]
                variant_channel.save()

            return 
        
        # get the first product type, ideally this should be the only type
        default_type = ProductType.objects.first()  

        name = product_data["item_name_e"] or product_data["item_name"] or ""

        product = Product(
            name=name,
            description=product_data["description_e"] or product_data["description"] or "",
            product_type=default_type,
            slug=slugify(name, allow_unicode=True)
        )
        product.save()

        product_variant = ProductVariant(
            product=product,
            sku=product_data["sparepart"],
            track_inventory=False
        )
        product_variant.save()

        product.default_variant = product_variant
        product.save()

        product_translation = ProductTranslation(
            product=product,
            language_code="ar",
            name=product_data["item_name"] or product_data["item_name"] or "",
            description=product_data["description"] or product_data["description_e"] or ""
        )
        product_translation.save()

        # publish in all channels
        for channel in Channel.objects.all():

            channel_listing = ProductChannelListing(
                product=product,
                channel=channel,
                visible_in_listings=True,
                available_for_purchase=datetime.datetime.now().date(),
                publication_date=datetime.datetime.now().date(),
                is_published=True
            )
            channel_listing.save()

            variant_channel_listing = ProductVariantChannelListing(
                variant=product_variant,
                channel=channel,
                currency=channel.currency_code,
                price_amount=product_data["item_price"],
                cost_price_amount=product_data["item_price"]
            )
            variant_channel_listing.save()

        
        if product_data["item_group_id"]:
            # attach attribute
            attribute = self._get_attribute("make", default_type)
            attribute_value = self._get_attribute_value(attribute, product_data["item_group_id"])

            associate_attribute_values_to_instance(product, attribute, attribute_value)


        print(product)


    def webhook(self, request: WSGIRequest, path: str, previous_value) -> HttpResponse:
        # check if plugin is active
        # check signatures and headers.
        if path == '/sync':
            # sync products with the external API
            try:
                api_data = requests.get(SYNC_URL, auth=(SYNC_USERNAME, SYNC_PASSWORD))
                api_data = api_data.json()

                product_data = api_data[12]
                self._add_product(product_data)
            except Exception as e:
                logger.error("[Product sync] Error syncing products")
                logger.exception(e)

            # do something with the request
            return JsonResponse(data={"paid":True})
        return HttpResponseNotFound()