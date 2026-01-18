import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from customers.models import Customer
from inventory.models import Product
from orders.models import (
    ContractCurtain,
    CurtainFabric,
    DraftOrder,
    DraftOrderItem,
    Order,
    OrderItem,
)
from orders.wizard_views import wizard_finalize

User = get_user_model()


def test_wizard_finalize_linking():
    # 1. Setup Data
    user = User.objects.first()
    customer = Customer.objects.first()
    product = Product.objects.first()
    if not product:
        print("❌ No product found")
        return

    # 2. Create Draft Order
    draft = DraftOrder.objects.create(
        created_by=user, customer=customer, status="draft", step=1
    )

    # 3. Add Draft Item
    draft_item = DraftOrderItem.objects.create(
        draft_order=draft, product=product, quantity=10, unit_price=100
    )

    # 4. Add Draft Curtain & Fabric linked to Item
    draft_curtain = ContractCurtain.objects.create(
        draft_order=draft, sequence=1, room_name="Test Room"
    )

    draft_fabric = CurtainFabric.objects.create(
        curtain=draft_curtain,
        draft_order_item=draft_item,
        fabric_name="Test Fabric",
        meters=5,
        sequence=1,
    )

    print(
        f"✅ Setup Complete. Draft Item ID: {draft_item.id}. Fabric Draft Item ID: {draft_fabric.draft_order_item.id}"
    )

    # 5. Simulate Finalize
    # We need to mock request session
    request = MagicMock()
    request.user = user
    request.session = {"wizard_draft_id": draft.id}

    # Prepare draft for finalize (steps completed)
    draft.completed_steps = [1, 2, 3, 4]
    draft.save()

    print("🚀 Running wizard_finalize...")
    from orders import wizard_views

    # Mock render/redirect to avoid HTTP response issues if any
    # But wizard_finalize returns JsonResponse or Redirect

    response = wizard_views.wizard_finalize(request)

    print(f"🏁 Finalize Result: {response}")

    # 6. Verify Sorting
    order = Order.objects.last()  # Should be the one created/updated
    if not order:
        print("❌ Order creation failed")
        return

    print(f"📦 Order Created: {order.order_number}")

    # Check CurtainFabric
    curtain = order.contract_curtains.first()
    if not curtain:
        print("❌ No curtain found in order")
        return

    fabric = curtain.fabrics.first()
    if not fabric:
        print("❌ No fabric found in curtain")
        return

    print(f"🧵 Fabric: {fabric.fabric_name}")
    print(f"🔗 Linked Order Item: {fabric.order_item}")

    if fabric.order_item:
        print(
            f"✅ Success! Fabric linked to Old Item ID: ?? New Item ID: {fabric.order_item.id}"
        )
        # Verify product match
        if fabric.order_item.product == product:
            print("✅ Product matches.")
        else:
            print("❌ Product mismatch.")
    else:
        print("❌ FAILURE! Fabric order_item is None.")

    # Check Cutting Order Items
    from cutting.models import CuttingOrderItem

    cutting_items = CuttingOrderItem.objects.filter(cutting_order__order=order)
    print(f"✂️ Cutting Items Count: {cutting_items.count()}")
    for item in cutting_items:
        print(
            f"   - {item.external_fabric_name if item.is_external else item.order_item.product.name} (External: {item.is_external})"
        )


if __name__ == "__main__":
    test_wizard_finalize_linking()
