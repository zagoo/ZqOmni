if [ "$(grep ZQ_ENVIRONMENT .env | cut -d '=' -f2)" = "dev" ]; then
  docker compose --profile dev up -d
else
  docker compose up -d
fi

