from django.core.exceptions import ValidationError
from urlextract import URLExtract

def validate_no_external_links(value, allowed_domains=('youtube.com', 'youtu.be')):
    """ Проверка на сторонние ссылки любого текста value"""
    if not value:
        return value
    url_extractor = URLExtract()
    urls = url_extractor.find_urls(value)

    for url in urls:
        # Приводим URL к нижнему регистру для сравнения
        url_lower = url.lower()

        # Проверяем, содержит ли URL разрешенные домены
        is_allowed = any(domain in url_lower for domain in allowed_domains)

        if not is_allowed:
            raise ValidationError('Запрещены ссылки на сторонние ресурсы.')

    return value
