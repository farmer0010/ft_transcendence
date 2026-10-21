COMPOSE ?= docker compose
SERVICES := mariadb redis ai backend notification-service nginx fe prometheus grafana backup uptime-kuma uptime-kuma-init
NPM ?= npm
JDBC_LOCAL := jdbc:mariadb://127.0.0.1:13306/cabi?serverTimezone=Asia/Seoul&useUnicode=true&characterEncoding=UTF-8&useSSL=false

.DEFAULT_GOAL := help
.PHONY: help env env-fe install-fe build build-backend build-notification build-fe up down reset seed logs logs-fe ps check check-fe check-ai fe run test backup restore dr-test

help:
	@echo "사용법: make <대상>"
	@echo ""
	@echo "  env       루트와 FE의 .env 가 없으면 예제 파일을 복사한다"
	@echo "  build     backend jar 와 FE 번들을 빌드한다 (테스트 제외, Node.js 22+ 필요)"
	@echo "  build-fe  FE 의존성 설치 후 타입 검사와 프로덕션 빌드를 실행한다"
	@echo "  up        빌드 후 docker compose 로 전체 스택을 띄우고 기동을 기다린다"
	@echo "  seed      사물함 시드(304개)를 DB 에 넣는다"
	@echo "  check     로그인 없이 호출할 수 있는 API 로 응답을 확인한다"
	@echo "  check-fe  FE 화면과 FE 프록시를 통한 공개 API 응답을 확인한다"
	@echo "  check-ai  AI 서버 /health 로 응답을 확인한다"
	@echo "  logs      백엔드 로그를 따라 본다"
	@echo "  logs-fe   FE 컨테이너 로그를 따라 본다"
	@echo "  fe        FE 개발 서버를 http://localhost:5173 에 띄운다 (Node.js 22+ 필요)"
	@echo "  ps        컨테이너 상태를 본다"
	@echo "  down      컨테이너를 내린다 (데이터는 남는다)"
	@echo "  reset     컨테이너와 데이터(db_data, redis_data)를 모두 지운다"
	@echo "  run       DB 와 Redis 만 compose 로 띄우고 gradlew bootRun 으로 실행한다"
	@echo "  test      backend 전체 테스트를 실행한다 (Docker 필요)"
	@echo "  backup    MariaDB/Redis 백업을 즉시 1회 실행한다"
	@echo "  restore   백업에서 복구한다 (예: make restore TARGET=mariadb FILE=cabi_20260101_000000.sql.gz)"
	@echo "  dr-test   백업 -> DB 초기화 -> 복구 -> 데이터 검증까지 자동으로 수행한다"

env: env-fe
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env 를 만들었습니다. 값을 확인하세요."; fi

env-fe:
	@if [ ! -f fe/.env ]; then cp fe/.env.example fe/.env && echo "fe/.env 를 만들었습니다."; fi

install-fe: env-fe
	$(NPM) --prefix fe ci --cache "$(CURDIR)/fe/.npm-cache"

build: build-backend build-notification build-fe

build-backend: env
	backend/gradlew -p backend clean build -x test

build-notification: env
	notification-service/gradlew -p notification-service clean build -x test

build-fe: install-fe
	$(NPM) --prefix fe run build

fe: install-fe
	$(NPM) --prefix fe run dev

up: build-backend build-notification
	$(COMPOSE) up -d --build --wait --wait-timeout 180 $(SERVICES)
	@$(MAKE) --no-print-directory check-fe
	@echo "기동했습니다."
	@echo "  FE       http://localhost:5173"
	@echo "  API      http://localhost"
	@echo "  Swagger  http://localhost/swagger-ui/index.html"
	@echo "  Grafana  http://localhost:3000 (admin / admin)"

seed: env
	@set -a; . ./.env; set +a; \
	docker exec -i cabi_db mariadb -u"$$DB_USER" -p"$$DB_PASSWORD" < backend/init_data.sql \
	&& echo "시드를 넣었습니다."

check:
	@curl -fsS http://localhost/v4/cabinets/status-summary/all && echo ""

check-fe:
	@curl -fsS -o /dev/null http://localhost:5173/ && echo "FE 화면 응답 정상"
	@curl -fsS http://localhost:5173/api/v4/cabinets/status-summary/all && echo ""

check-ai:
	@curl -fsS http://127.0.0.1:8000/health && echo ""

logs:
	$(COMPOSE) logs -f backend

logs-fe:
	$(COMPOSE) logs -f fe

ps:
	$(COMPOSE) ps

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v
	rm -rf db_data redis_data

run: env
	$(COMPOSE) up -d mariadb redis
	@echo "DB 기동을 기다립니다 (최대 60초)"
	@set -a; . ./.env; set +a; i=0; \
	until docker exec cabi_db mariadb-admin ping -h127.0.0.1 -u"$$DB_USER" -p"$$DB_PASSWORD" --silent >/dev/null 2>&1; do \
		i=$$((i+1)); \
		if [ $$i -gt 30 ]; then echo "DB 가 뜨지 않았습니다."; exit 1; fi; \
		sleep 2; \
	done
	@set -a; . ./.env; set +a; \
	DB_HOST=127.0.0.1 DB_PORT=13306 REDIS_ALLOW_INSECURE=true \
	SPRING_DATASOURCE_URL='$(JDBC_LOCAL)' \
	SPRING_CLOUD_AZURE_STORAGE_BLOB_CONNECTION_STRING="$$AZURE_STORAGE_CONNECTION_STRING" \
	SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_42_REDIRECT_URI="$$FRONTEND_URL/login/oauth2/code/42" \
	SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_KAKAO_REDIRECT_URI="$$FRONTEND_URL/login/oauth2/code/kakao" \
	SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_REDIRECT_URI="$$FRONTEND_URL/login/oauth2/code/google" \
	backend/gradlew -p backend bootRun

test:
	backend/gradlew -p backend clean test

backup:
	$(COMPOSE) exec backup /scripts/backup.sh

restore:
	$(COMPOSE) exec backup /scripts/restore.sh $(TARGET) $(FILE)

dr-test:
	./scripts/dr-test.sh
