default:
	@just --list --unsorted

run:
	doppler run -- docker compose -f docker-compose.dev.yml up

run-prod:
	doppler run -- docker compose -f docker-compose.yml up -d

build:
	doppler run -- docker compose -f docker-compose.dev.yml build

pushdb:
	doppler run -- docker compose -f docker-compose.dev.yml run --rm -e POSTGRES_DSN=$(doppler secrets get POSTGRES_DSN --plain) bot prisma db push

pushdb-prod:
	doppler run -- docker compose -f docker-compose.yml run --rm -e POSTGRES_DSN=$(doppler secrets get POSTGRES_DSN --plain) bot prisma db push