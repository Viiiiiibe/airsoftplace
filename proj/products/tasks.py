from proj.celery import app
from .models import Product
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from cart.models import Order
from .utils import get_product_text
from scipy.sparse import hstack, csr_matrix
from sklearn.preprocessing import MinMaxScaler
# import matplotlib.pyplot as plt


@app.task
def find_recommended_products_for_user(user_pk, viewed_product_ids=None):
    """
        Находит и кеширует персональные рекомендации для пользователя:
        - учитываются покупки за последние 3 месяца (Order.created)
        - последние просмотры из переданного списка viewed_product_ids
        Результат — список из топ‑10 товаров, схожих по TF‑IDF профилю.
        """
    queryset = Q(verified=True) & Q(show=True) & Q(items_left__gt=0)
    now = timezone.now()
    three_months_ago = now - timedelta(days=90)

    # 1) Собираем купленные за 3 месяца товары
    purchased_ids = (
        Order.objects
        .filter(user__pk=user_pk, created__gte=three_months_ago)
        .values_list('items__product', flat=True)
        .distinct()
    )

    # 2) Используем переданный из сессии список последних просмотров
    if viewed_product_ids is None:
        viewed_product_ids = []
    else:
        # приводим к уникальным целым
        viewed_product_ids = list({int(pid) for pid in viewed_product_ids})

    # 3) Объединяем взаимодействия
    interacted_ids = set(purchased_ids) | set(viewed_product_ids)

    if interacted_ids:
        # 4) Товары пользователя и кандидаты
        user_prods = list(Product.objects.filter(id__in=interacted_ids))
        candidates = list(
            Product.objects
            .filter(queryset)
            .exclude(id__in=interacted_ids)
        ) or list(Product.objects.filter(queryset))

        # 5) Тексты для TF-IDF
        user_texts = [get_product_text(p) for p in user_prods]
        cand_texts = [get_product_text(p) for p in candidates]

        vectorizer = TfidfVectorizer(stop_words='english')
        cand_tfidf = vectorizer.fit_transform(cand_texts)
        user_tfidf = vectorizer.transform(user_texts)

        # 6) Нормализация цены (MinMax → [0,1])
        cand_prices = np.array([p.price for p in candidates]).reshape(-1, 1)
        user_prices = np.array([p.price for p in user_prods]).reshape(-1, 1)
        scaler = MinMaxScaler()  # нормирует в диапазон [0,1] :contentReference[oaicite:0]{index=0}
        scaler.fit(np.vstack([cand_prices, user_prices]))
        cand_price_norm = scaler.transform(cand_prices)
        user_price_norm = scaler.transform(user_prices)

        # 7) Преобразуем цены в CSR и объединяем с TF-IDF :contentReference[oaicite:1]{index=1}
        cand_price_sp = csr_matrix(cand_price_norm)
        user_price_sp = csr_matrix(user_price_norm)

        cand_combined = hstack([cand_tfidf, cand_price_sp])
        user_combined = hstack([user_tfidf, user_price_sp])

        # 8) Профиль пользователя и вычисление cosine_similarity
        # ----- Вот ключевое изменение: превращаем numpy.matrix в ndarray -----
        raw_profile = user_combined.mean(axis=0)  # это возвращает numpy.matrix :contentReference[oaicite:0]{index=0}
        user_profile = np.asarray(raw_profile)  # теперь обычный numpy.ndarray :contentReference[oaicite:1]{index=1}
        sims = cosine_similarity(user_profile, cand_combined)[0]

        # 9) Сортировка
        scored = sorted(zip(candidates, sims), key=lambda x: x[1], reverse=True)

        # Выбираем топ-10 наиболее похожих товаров и кешируем на 1 час
        cache.set(f"recommended_products_cache_user_{user_pk}", [prod for prod, _ in scored[:10]],
                  60 * 60)

        # plt.figure()
        # plt.hist(sims, bins=20)
        # plt.xlabel('Косинусное сходство')
        # plt.ylabel('Кол-во товаров')
        # plt.title('Гистограмма распределения сходства')
        # plt.show()
