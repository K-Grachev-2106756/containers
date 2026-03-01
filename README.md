# Контейнеризация и оркестрация

## hw 1

### Сборка
```
docker build -t auth-service ./auth
```

### Запуск
volume - db.json файл на хосте, при перезапуске контейнера не удаляется.
```
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/auth/data:/app/data \
  --name auth \
  auth-service
```

### Пример запроса
```
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"1","password":"2"}'
```

### Dockerfile-bad:
1) `FROM python:latest`
- Непредсказуемые сборки, т.к. тег latest перепривязывается к самой актуальной версии
- Невозможно воспроизвести окружение

как исправлено: `FROM python:3.11-slim`
(кстати slim - урезанная версия для минимизации размера контейнера)

2) `COPY . .`
- Эта команда копирует все подряд, в т.ч. `.git`, `__pychache__`, `.env`, другие локальные данные

как исправлено: 
```
COPY requirements.txt .
COPY app.py .
```

3) `CMD ["python", "app.py"]`
- Нет ASGI
- Нет graceful shutdown

как исправлено:
```
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Bad practices для этого проекта

1) Запуск контейнера без volume на хосте ведет к потере данных при перезапуске контейнера
```
docker run auth-service
```

2) Не указывать версии библиотек в requirements.txt - ведет к непредсказуемости сборки, а также увеличении времени сборки слоя, отвечающего за установку зависимостей

3) Хранение данных в json ведет к поиску за o(N) итераторами питона без оптимизаций, предлагаемых СУБД

4) Взвалить на auth-service функционал, который не относится к взаимодействию с записями о пользователях - нарушение "single responsibility"

### Когда контейнеры не нужны

1) Если имеем дело с одноразовыми скриптами, а не микросервисами

- Запуск напрямую будет быстрее и проще, без лишних Dockerfile и docker команд

2) Для GUI приложений

- Сложный доступ к GUI/GPU
- Контейнеры предназначены для серверных рабочих нагрузок


## hw 2

### Общая структура

Три сервиса объединены в одну сеть `auth_net`:

1. `db` - база данных MySQL
2. `db_init` - одноразовый сервис для инициализации схемы БД (выполняет скрипт и завершает работу)
3. `auth` - FastAPI сервис для аутентификации (sign-up / login)

Все переменные окружения вынесены в файл `.env`.

### Описание сервисов

1) `db` (MySQL)
- Образ: `mysql:8.0`
- Container name: `auth_mysql`
- Volumes:
  - `./mysql_data:/var/lib/mysql` (для сохранности данных между рестартами)
- Ports: `3306:3306` (прокидывание порта наружу)
- Healthcheck: проверяет доступность сервера MySQL через `mysqladmin ping`
- Зависимости: на него опирается сервис `db_init` и `auth`

2) `db_init`
- Образ: `mysql:8.0` (одноразовый контейнер)
- Container name: `auth_db_init`
- Depends_on: `db` с условием `service_healthy` (чтобы инициализация не стартовала раньше, чем БД готова)
- Volumes: монтирует `init.sql` для инициализации схемы
- Command: выполняет SQL-скрипт и завершает работу
- Назначение: создать базу данных и таблицы (`users`, `sessions`) при первом запуске

3) `auth`
- Сборка: из локального Dockerfile (`./auth/Dockerfile`), имя образа `auth-service:latest`
- Container name: `auth_app`
- Depends_on: `db` (подождёт пока БД доступна)
- Ports: `8000:8000`
- Command: запускает FastAPI сервер через uvicorn
- Назначение: предоставляет REST API для регистрации и логина пользователей
- Связь с БД: использует PyMySQL для подключения к `db`

### Сеть

Все сервисы подключены к одной сети `auth_net` (driver: bridge), что позволяет контейнерам обращаться друг к другу по имени сервиса.


### Как управлять ресурсами сервисов

В `docker-compose.yml` можно задавать лимиты ресурсов (CPU, память) для каждого сервиса.  
Пример для сервиса `auth`:

```
services:
  auth:
    build: ./auth
    mem_limit: 512m
    cpus: 0.5
```

### Как запустить только один сервис

```
docker-compose up auth
```
Остальные сервисы не стартуют, кроме тех, от которых зависит auth через depends_on.


## hw 3

### Проверка, что куб установлен
![check_kube](/report_source/hw_3_1_check_kube.png)

### Создание ресурсов postgres
![create_resources](/report_source/hw_3_2_create_resources.png)

Порядок выполнения манифестов важен - ресурсы должны существовать до того как их начнут использовать.
К примеру, Secret и ConfigMap должны создаваться раньше пода, т.к. переменные этих ресурсов используются в Deployment секции.

### Проверка ресурсов postgres
![check_resources](/report_source/hw_3_3_check_resources.png)

### Создание ресурсов nextcloud
![create_nextcloud](/report_source/hw_3_4_create_nextcloud.png)

### Логи пода nextcloud
![nextcloud_logs](/report_source/hw_3_5_nextcloud_logs.png)

### Перенаправленный порт nextcloud
![nextcloud_port](/report_source/hw_3_6_nextcloud_port.png)

### Веб-интерфейс nextcloud
![nextcloud_works](/report_source/hw_3_7_nextcloud_works.png)

Если вдруг выключить postgres:
```
kubectl scale deployment postgres --replicas=0
```
  -> `deployment.apps/postgres scaled`

  -> Веб-интерфейс выдает `"Не удаётся установить соединение с сайтом, Соединение было прервано."`
```
kubectl get pods
``` 
  -> остался только под nextcloud
```
kubectl logs nextcloud-67dd7c8d98-7htbn
```
  -> `"GET /status.php HTTP/1.1" 500 410 "-" "kube-probe/1.34"`

  -> `[mpm_prefork:notice] [pid 1:tid 1] AH00170: caught SIGWINCH, shutting down gracefully`

```
kubectl get pods
```
  -> Под nextcloud начал перезапускаться

```
kubectl scale deployment postgres --replicas=1
```
  -> Под postgres появился
  
  -> Под nextcloud перезапустился

  -> Веб-интерфейс снова доступен

```
kubectl get pvc
```
  -> No resources found in default namespace.

Таким образом, postgres развёрнут через Deployment без PersistentVolume.
При масштабировании реплик до 0 Pod удаляется, вместе с временным хранилищем.
При повторном запуске база инициализируется заново с теми же кредами, но без старых данных.

### Веб-интерфейс kubernetes
![kubernetes_UI](/report_source/hw_3_8_kubernetes_UI.png)

### Проверка secret для postgres
![create_postgres_secret](/report_source/hw_3_9_create_postgres_secret.png)

### Проверка configmap для nextcloud
![create_nextcloud_configmap](/report_source/hw_3_10_create_nextcloud_configmap.png)

### Работа liveness readiness проб
![nextcloud_liveness_readiness](/report_source/hw_3_11_nextcloud_liveness_readiness.png)


## hw 4

### Сборка и запуск

1) Добавляем локальный образ внутрь куба

powershell:
```
minikube docker-env | Invoke-Expression
```
bash:
```
eval $(minikube docker-env)
```
Собираем образ:
```
docker build -t auth-service:latest ./auth/.
```

2) Добавляем ресурсы:
```
cd ./kube-prj
kubectl create -f ./mysql-secret.yml
kubectl create -f ./mysql-pvc.yml
kubectl create -f ./mysql-init.yml
kubectl create -f ./mysql-service.yml
kubectl create -f ./mysql-deployment.yml
kubectl create -f ./auth-configmap.yml
kubectl create -f ./auth-service.yml
kubectl create -f ./auth-deployment.yml
```

В mysql-deployment.yml запускается скрипт для инициализации таблиц:
```
initContainers:
  - name: render-init-sql
    image: alpine:3.18
    env:
      - name: MYSQL_USER
        valueFrom:
          secretKeyRef:
            name: mysql-secret
            key: MYSQL_USER
      - name: MYSQL_PASSWORD
        valueFrom:
          secretKeyRef:
            name: mysql-secret
            key: MYSQL_PASSWORD
    command:
      - sh
      - -c
      - |
        apk add --no-cache gettext
        echo "Rendering init.sql"
        envsubst < /tpl/init.sql.tpl > /out/init.sql
        cat /out/init.sql
    volumeMounts:
      - name: mysql-init-tpl
        mountPath: /tpl
      - name: mysql-init-final
        mountPath: /out
```

Проверяем, что скрипт отработал успешно и таблицы создались:
![mysql_ready](/report_source/hw_4_1_mysql_ready.png)

Проверяем, что сервис auth поднялся:
![service_healthcheck](/report_source/hw_4_2_service_healthcheck.png)

3) Запуск сервиса:
```
minikube service auth
```

Проверка работы (логин по несуществующим кредам):
```
curl -X POST http://127.0.0.1:50515/login  \
-H "Content-Type: application/json"  \
-d '{"email":"1","password":"2"}'
```
> {"detail":"Invalid credentials"}

Из логов mysql:
> INFO:     10.244.0.1:24945 - "POST /login HTTP/1.1" 401 Unauthorized

Такое поведение является ожидаемым.

Таким образом, все работает.
