

docker-compose := "docker compose"

run:
    just runserver

runserver *args:
    {{docker-compose}} up -d {{args}}
    just logs

logs *args:
    {{docker-compose}} logs -f {{args}}

down *args:
    {{docker-compose}} down {{args}}

migrate:
    {{docker-compose}} run --rm web python manage.py migrate

createsuperuser:
    {{docker-compose}} run --rm web python manage.py createsuperuser

makemigrations:
    {{docker-compose}} run --rm web python manage.py makemigrations

build:
    {{docker-compose}} build