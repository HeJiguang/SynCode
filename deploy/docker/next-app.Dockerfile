FROM node:22-bookworm-slim AS build

ARG APP_NAME

WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json frontend/tsconfig.base.json frontend/README.md ./
COPY frontend/apps ./apps
COPY frontend/packages ./packages

RUN npm ci
RUN npm run build -w "@aioj/${APP_NAME}"

FROM node:22-bookworm-slim

ARG APP_NAME

ENV NODE_ENV=production

WORKDIR /app/frontend
COPY --from=build /workspace/frontend /app/frontend

EXPOSE 3000
ENTRYPOINT ["sh", "-c", "npm run start -w @aioj/${APP_NAME} -- --hostname 0.0.0.0 --port 3000"]
