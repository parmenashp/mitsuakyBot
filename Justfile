default:
	@just --list

run:
	doppler run -- docker compose -f docker-compose.dev.yml up

build:
	doppler run -- docker compose -f docker-compose.dev.yml build

pushdb:
	doppler run -- docker compose -f docker-compose.dev.yml run --rm -e POSTGRES_DSN=$(doppler secrets get POSTGRES_DSN --plain) bot prisma db push