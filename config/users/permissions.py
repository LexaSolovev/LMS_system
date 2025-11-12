from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Разрешает доступ только владельцу объекта.
    """

    def has_object_permission(self, request, view, obj):
        # Проверяем владельца через поле owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        return False


class IsModerator(BasePermission):
    """
    Permission проверяет, является ли пользователь модератором.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='moderators').exists()


class IsOwnerOrModerator(BasePermission):
    """
    Разрешает доступ владельцу объекта или модератору.
    Для модераторов - полный доступ, для владельцев - доступ к своим объектам.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Модераторы могут читать и редактировать любые объекты
        if request.user.groups.filter(name='moderators').exists():
            return True

        # Владелец может делать все со своим объектом
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        return False


class IsOwnerOrModeratorForCreate(BasePermission):
    """
    Разрешает создание объектов только владельцам (не модераторам).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Модераторы не могут создавать объекты
        if request.user.groups.filter(name='moderators').exists():
            return False

        return True


class IsOwnerOrModeratorForList(BasePermission):
    """
    Разрешает список объектов: модераторы видят все, обычные пользователи - только свои.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated