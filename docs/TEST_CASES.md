# Приймальні тест-кейси (C1)

Фіксований список. Колонка «Автотест» вказує, який тест у `backend/tests/` це перевіряє.
Для захисту додай скріншоти (Swagger `/docs` або UI) у колонку «Підтвердження».

| № | Кейс | Кроки | Очікуваний результат | Автотест | Результат |
|---|---|---|---|---|---|
| TC-01 | Реєстрація клієнта | POST /auth/register | 201, пароль не повертається | test_register_and_login | ✅ |
| TC-02 | Вхід | POST /auth/login | 200, JWT | test_register_and_login | ✅ |
| TC-03 | Вхід з хибним паролем | POST /auth/login | 401 | test_login_wrong_password | ✅ |
| TC-04 | Створення профілю майстра | POST /masters | 201 | test_get_master_and_services | ✅ |
| TC-05 | Додавання послуги і графіку | POST /masters/me/services, PUT /masters/me/schedule | 201 / 200 | фікстура `master` | ✅ |
| TC-06 | Пошук за містом | GET /masters?city=… | у відповіді лише майстри міста | test_search_filters | ✅ |
| TC-07 | Фільтр за ціною та рейтингом | GET /masters?min_price=…&min_rating=… | коректна вибірка | test_search_filters, test_review_flow_updates_rating | ✅ |
| TC-08 | Перегляд вільних слотів | GET /masters/{id}/slots | список слотів з кроком 30 хв | test_slots_listed | ✅ |
| TC-09 | Запис на послугу | POST /bookings | 201, слот зникає зі списку | test_create_booking_and_slot_disappears | ✅ |
| TC-10 | Подвійне бронювання | два POST /bookings на той самий час | другий — 409 | test_double_booking_rejected | ✅ |
| TC-11 | Скасування запису | POST /bookings/{id}/cancel | статус cancelled, слот вільний | test_cancel_frees_slot | ✅ |
| TC-12 | Перенесення запису | POST /bookings/{id}/reschedule | новий час, старий вільний | test_reschedule | ✅ |
| TC-13 | Історія записів | GET /bookings/my | свої записи (клієнт/майстер) | test_my_bookings | ✅ |
| TC-14 | Відгук після візиту | POST /reviews | 201, рейтинг майстра оновлено | test_review_flow_updates_rating | ✅ |
| TC-15 | Відгук до візиту | POST /reviews | 400 | test_review_before_visit_rejected | ✅ |

Запуск усіх: `cd backend && pytest`. Результат: **58 passed**.
