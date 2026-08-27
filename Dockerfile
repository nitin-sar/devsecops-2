FROM node:20-alpine

WORKDIR /app

COPY package.json yarn.lock ./

RUN corepack enable && yarn install --frozen-lockfile --production=true && yarn cache clean

COPY src ./src

ENV NODE_ENV=production \
    LISTEN_PORT=3000

EXPOSE 3000

USER node

CMD ["node", "-r", "dotenv/config", "src/index.js"]