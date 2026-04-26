# BPMSoft ML Gateway

ML API-шлюз для интеграции с BPMSoft.

В репозитории:
- [Backend/README.md](Backend/README.md) — основная документация, quickstart, архитектура и демонстрационные материалы
- `Karina/` — готовый артефакт demand-модели и её исходный ML-контур
- `Vlad/` — placeholder под будущий pricing-модуль

Быстрый старт:

```bash
cd Backend
python3.11 -m pip install -r requirements.txt
cp .env.example .env
make api
```

Dashboard:

```bash
cd Backend
make dashboard
```
