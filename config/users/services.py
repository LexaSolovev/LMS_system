import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """
    Сервис для работы с Stripe API
    """

    @staticmethod
    def create_product(name, description=None):
        """
        Создание продукта в Stripe
        """
        try:
            product = stripe.Product.create(name=name, description=description)
            return product
        except stripe.error.StripeError as e:
            raise Exception(f"Ошибка создания продукта в Stripe: {str(e)}")

    @staticmethod
    def create_price(product_id, amount, currency="rub"):
        """
        Создание цены в Stripe
        amount: сумма в рублях (будет преобразована в копейки)
        """
        try:
            # Преобразуем рубли в копейки
            amount_in_cents = int(amount * 100)

            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount_in_cents,
                currency=currency,
            )
            return price
        except stripe.error.StripeError as e:
            raise Exception(f"Ошибка создания цены в Stripe: {str(e)}")

    @staticmethod
    def create_checkout_session(price_id, success_url, cancel_url, metadata=None):
        """
        Создание сессии для оплаты
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            return session
        except stripe.error.StripeError as e:
            raise Exception(f"Ошибка создания сессии в Stripe: {str(e)}")

    @staticmethod
    def retrieve_session(session_id):
        """
        Получение информации о сессии
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            raise Exception(f"Ошибка получения сессии из Stripe: {str(e)}")

    @staticmethod
    def create_payment_for_course_or_lesson(payment_instance):
        """
        Создание платежа в Stripe для курса или урока
        """
        if payment_instance.paid_course:
            item = payment_instance.paid_course
            item_type = "course"
        elif payment_instance.paid_lesson:
            item = payment_instance.paid_lesson
            item_type = "lesson"
        else:
            raise Exception("Не указан курс или урок для оплаты")

        # Создаем продукт
        product = StripeService.create_product(
            name=item.name, description=item.description
        )

        # Создаем цену
        price = StripeService.create_price(
            product_id=product.id, amount=payment_instance.amount
        )

        # Создаем сессию для оплаты
        success_url = f"{settings.DOMAIN}/api/users/payments/success/?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.DOMAIN}/api/users/payments/cancel/"

        session = StripeService.create_checkout_session(
            price_id=price.id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "payment_id": str(payment_instance.id),
                "item_type": item_type,
                "item_id": str(item.id),
                "user_id": str(payment_instance.user.id),
            },
        )

        # Обновляем платеж данными из Stripe
        payment_instance.stripe_product_id = product.id
        payment_instance.stripe_price_id = price.id
        payment_instance.stripe_session_id = session.id
        payment_instance.payment_method = "stripe"
        payment_instance.status = "pending"
        payment_instance.save()

        return session
