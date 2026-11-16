# Build from the repository root: docker build -f packages/api/Dockerfile .
FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
COPY packages/shared packages/shared
COPY packages/api packages/api
RUN npm install --omit=dev --workspace @shop/api
USER node
EXPOSE 3000
CMD ["node", "packages/api/src/server.js"]
