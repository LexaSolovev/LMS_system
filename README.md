# Materials
GET/POST    /api/materials/courses/

GET/PUT/DEL /api/materials/courses/{id}/

GET/POST    /api/materials/lessons/

GET/PUT/DEL /api/materials/lessons/{id}/

# Users
GET/POST    /api/users/users/

GET/PUT/DEL /api/users/users/{id}/

GET/POST    /api/users/payments/

GET/PUT/DEL /api/users/payments/{id}/


# Фильтрация платежей:
GET /api/users/payments/?paid_course=1

GET /api/users/payments/?paid_lesson=1

GET /api/users/payments/?payment_method=cash

GET /api/users/payments/?ordering=payment_date  (по возрастанию)

GET /api/users/payments/?ordering=-payment_date (по убыванию)
